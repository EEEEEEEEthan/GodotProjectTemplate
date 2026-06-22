"""用户↔主程(需求)→/execute→主程(设计)→实现→优化→全量测试→审查→用户验收→提交 流水线编排。"""

import subprocess
from contextlib import contextmanager
from pathlib import Path

from cursor_sdk import Client

from agent_session import AgentSession, load_role_prompt, print_role
from config import (
    MAX_ACCEPTANCE_CYCLES,
    MAX_EXECUTOR_ROUNDS,
    MAX_REDO_CYCLES,
    MAX_REVIEW_CYCLES,
    PROJECT_ROOT,
    ensure_cursor_api_key_env,
)
from git_ops import git_clean_worktree, git_commit_all, git_diff, git_push
from loop_log import LoopRunLogger
from markers import (
    AcceptanceVerdict,
    ReviewVerdict,
    extract_block,
    has_executor_done,
    has_git_clean_request,
    parse_acceptance,
    parse_review,
)


class WorkflowOrchestrator:
    def __init__(
        self,
        client: Client,
        project_root: Path = PROJECT_ROOT,
        run_logger: LoopRunLogger | None = None,
    ) -> None:
        self.client = client
        self.project_root = project_root
        self.api_key = ensure_cursor_api_key_env()
        self._run_logger = run_logger
        self._executor: AgentSession | None = None
        self._executor_index = 0
        self._executor_phase = "implement"

    def _log(self, tag: str, text: str) -> None:
        print_role(tag, text, run_logger=self._run_logger)

    def _executor_tag(self) -> str:
        return f"executor#{self._executor_index}/{self._executor_phase}"

    def _close_executor(self) -> None:
        if self._executor is not None:
            self._executor.close()
            self._executor = None

    def _open_executor(self, executor_index: int, *, phase: str) -> None:
        self._close_executor()
        self._executor_index = executor_index
        self._executor_phase = phase
        self._executor = AgentSession(
            "executor",
            load_role_prompt(f"executor-{phase}"),
            console_tag=self._executor_tag(),
            client=self.client,
            mode="agent",
            api_key=self.api_key,
            cwd=self.project_root,
            run_logger=self._run_logger,
        )

    @contextmanager
    def _lead_session(self):
        with AgentSession(
            "lead",
            load_role_prompt("lead"),
            client=self.client,
            mode="plan",
            api_key=self.api_key,
            cwd=self.project_root,
            echo_plan=True,
            run_logger=self._run_logger,
        ) as lead:
            yield lead

    def _run_executor_until_done(
        self,
        initial_message: str,
        *,
        orchestrator_gate: bool = False,
    ) -> None:
        if self._executor is None:
            raise RuntimeError("执行程序会话未打开")
        label = self._executor_tag()
        message = initial_message
        for round_index in range(1, MAX_EXECUTOR_ROUNDS + 1):
            text = self._executor.send(message)
            if has_executor_done(text):
                if not orchestrator_gate:
                    return
                passed, output = self._run_autotest()
                if passed:
                    self._log("系统", f"{label} 编排器全量测试通过。")
                    return
                message = (
                    f"编排器全量测试未通过（第 {round_index} 轮），请修复：\n\n{output}"
                )
                continue
            message = (
                "未检测到 EXECUTOR_DONE。请继续，或完成后输出 EXECUTOR_DONE 块。"
            )
        raise RuntimeError(f"{label} 超过最大轮次 ({MAX_EXECUTOR_ROUNDS})")

    def _run_orchestrator_gate(self, executor_index: int) -> None:
        passed, output = self._run_autotest()
        if passed:
            self._log("系统", f"executor#{executor_index} 编排器全量测试通过。")
            return
        self._open_executor(executor_index, phase="implement")
        self._run_executor_until_done(
            f"编排器全量测试未通过，请修复：\n\n{output}",
            orchestrator_gate=True,
        )

    def run(self) -> None:
        banner = (
            f"=== Dev Loop ===\n"
            f"项目: {self.project_root}\n"
            f"主程: 定稿需求后输入 /execute（主程随后出方案再实现）；验收满意后输入 /accept"
        )
        print(f"{banner}\n")
        if self._run_logger is not None:
            self._run_logger.log_banner(banner)
        try:
            self._run_pipeline()
        finally:
            self._close_executor()

    def _run_pipeline(self) -> None:
        requirements, design = self._phase_intake()
        executor_index = 1
        redo_count = 0
        need_execute = True

        while True:
            if need_execute:
                self._phase_execute(requirements, design, executor_index)
                need_execute = False

            review = self._phase_review(requirements, design, executor_index)
            if review.verdict == ReviewVerdict.FIX:
                self._phase_execute_fix(requirements, design, review.feedback)
                continue

            if review.verdict == ReviewVerdict.REDO:
                advanced = self._advance_after_redo(
                    requirements=requirements,
                    design=design,
                    feedback=review.feedback,
                    design_revision=review.design_revision,
                    clean_reason="主程审查要求重做",
                    redo_count=redo_count,
                    executor_index=executor_index,
                )
                if advanced is None:
                    return
                executor_index, design, redo_count = advanced
                need_execute = True
                continue

            acceptance = self._phase_acceptance(requirements, design, executor_index)
            if acceptance.verdict == AcceptanceVerdict.PASS:
                self._git_commit_and_push(acceptance.commit_message)
                self._log("系统", "验收通过，已提交并推送，流程结束。")
                return

            if acceptance.verdict == AcceptanceVerdict.FIX:
                self._log("系统", "验收未通过，在当前基础上修复。")
                self._phase_execute_fix(requirements, design, acceptance.feedback)
                continue

            advanced = self._advance_after_redo(
                requirements=requirements,
                design=design,
                feedback=acceptance.feedback,
                design_revision=acceptance.design_revision,
                clean_reason="验收未通过，主程要求重做",
                redo_count=redo_count,
                executor_index=executor_index,
            )
            if advanced is None:
                return
            executor_index, design, redo_count = advanced
            need_execute = True

    def _phase_intake(self) -> tuple[str, str]:
        with self._lead_session() as lead:
            requirements: str | None = None
            while True:
                user_input = input("你> ").strip()
                if not user_input:
                    continue
                if self._run_logger is not None:
                    self._run_logger.log_user(user_input)
                if user_input == "/execute":
                    if not requirements:
                        self._log(
                            "系统",
                            "尚无 REQUIREMENTS，请继续与主程对话直至其输出需求块。",
                        )
                        continue
                    self._log("系统", "需求已定稿，请主程输出方案...")
                    design_prompt = (
                        "用户已发送 /execute。请根据已定稿需求输出 DESIGN 方案块。\n\n"
                        f"已定稿需求：\n{requirements}"
                    )
                    for cycle in range(1, MAX_REVIEW_CYCLES + 1):
                        prompt = design_prompt
                        if cycle > 1:
                            prompt = (
                                "未解析到有效 DESIGN 块，请严格按格式重新输出。\n\n"
                                + prompt
                            )
                        lead.send(prompt)
                        if block := extract_block(
                            lead.text_for_block_extraction(), "DESIGN"
                        ):
                            self._log("系统", "开始实现...")
                            return requirements, block
                    raise RuntimeError("主程未输出有效 DESIGN 块")
                lead.send(user_input)
                extraction_text = lead.text_for_block_extraction()
                if block := extract_block(extraction_text, "REQUIREMENTS"):
                    requirements = block

    def _phase_design_revision(
        self, requirements: str, design: str, feedback: str
    ) -> str:
        with self._lead_session() as lead:
            lead.send(
                "审查结论为 redo。请修订方案（DESIGN 块），避免下一任执行程序重复犯错。\n\n"
                f"原需求：\n{requirements}\n\n原方案：\n{design}\n\n审查意见：\n{feedback}"
            )
            revised = extract_block(lead.text_for_block_extraction(), "DESIGN")
        if not revised:
            raise RuntimeError("主程未输出修订后的 DESIGN 块")
        return revised

    def _phase_execute(
        self, requirements: str, design: str, executor_index: int
    ) -> None:
        self._open_executor(executor_index, phase="implement")
        task = (
            f"需求：\n{requirements}\n\n方案：\n{design}\n\n"
            "请实现并编写/更新自动化测试，跑通相关单测后输出 EXECUTOR_DONE。"
        )
        self._log("系统", f"执行程序 #{executor_index}：实现阶段")
        self._run_executor_until_done(task)
        self._phase_optimize(executor_index)
        self._log("系统", f"执行程序 #{executor_index}：编排器全量测试门禁")
        self._run_orchestrator_gate(executor_index)

    def _phase_optimize(self, executor_index: int) -> None:
        diff = git_diff(self.project_root)
        if not diff.strip():
            self._log("系统", "无 git diff，跳过代码优化。")
            return
        self._open_executor(executor_index, phase="optimize")
        self._log("系统", f"executor#{executor_index}：代码优化阶段（新会话）")
        self._run_executor_until_done("实现阶段已完成，请开始优化。")

    def _phase_execute_fix(
        self,
        requirements: str,
        design: str,
        feedback: str,
    ) -> None:
        executor_index = self._executor_index
        self._open_executor(executor_index, phase="implement")
        message = (
            f"主程审查要求修复（verdict=fix）：\n{feedback}\n\n"
            f"需求：\n{requirements}\n\n方案：\n{design}\n\n"
            "请小步修改，完成后输出 EXECUTOR_DONE。"
        )
        self._run_executor_until_done(message, orchestrator_gate=True)

    def _phase_review(
        self, requirements: str, design: str, executor_index: int
    ):
        with self._lead_session() as lead:
            for cycle in range(1, MAX_REVIEW_CYCLES + 1):
                prompt = (
                    f"请审查执行程序 #{executor_index} 的实现（对照 git diff）。\n\n"
                    f"需求：\n{requirements}\n\n方案：\n{design}\n\n"
                    "输出 REVIEW 块（verdict=pass|fix|redo）。"
                )
                if cycle > 1:
                    prompt = (
                        "未解析到有效 REVIEW 块，请严格按格式重新输出。\n\n" + prompt
                    )
                text = self._lead_reply_after_git_clean(
                    lead,
                    lead.send(prompt),
                    clean_reason="主程审查要求清空工作区",
                    retry_prompt=(
                        "工作区已 git clean。请输出 REVIEW 块，verdict=redo，并附 DESIGN_REVISION。"
                    ),
                )
                review = parse_review(text)
                if review:
                    self._log(
                        "系统",
                        f"审查结果: {review.verdict.value}（第 {cycle} 轮）",
                    )
                    return review
        raise RuntimeError("主程审查未产出有效 REVIEW")

    def _phase_acceptance(
        self, requirements: str, design: str, executor_index: int
    ):
        self._log("系统", "代码审查已通过，进入用户验收。请实测并与主程确认是否符合预期。")
        with self._lead_session() as lead:
            lead.send(
                "代码审查已通过，进入用户验收阶段。请引导用户对照需求与方案实测验收。\n\n"
                f"需求：\n{requirements}\n\n方案：\n{design}\n\n"
                "用户满意时输出 ACCEPTANCE verdict=pass（须含 COMMIT_MESSAGE）；"
                "可小修则 verdict=fix；须重做则 verdict=redo 并附 DESIGN_REVISION。"
            )
            for cycle in range(1, MAX_ACCEPTANCE_CYCLES + 1):
                while True:
                    user_input = input("你> ").strip()
                    if not user_input:
                        continue
                    if self._run_logger is not None:
                        self._run_logger.log_user(user_input)
                    if user_input == "/accept":
                        text = lead.send(
                            "用户表示验收通过。请输出 ACCEPTANCE verdict=pass，"
                            "并附中文 COMMIT_MESSAGE（一句话主题 + 空行 + 补充说明）。"
                        )
                    else:
                        text = lead.send(user_input)
                    text = self._lead_reply_after_git_clean(
                        lead,
                        text,
                        clean_reason="主程验收阶段要求清空工作区",
                        retry_prompt=(
                            "工作区已 git clean。请输出 ACCEPTANCE verdict=redo，并附 DESIGN_REVISION。"
                        ),
                    )
                    acceptance = parse_acceptance(lead.text_for_block_extraction())
                    if acceptance:
                        self._log(
                            "系统",
                            f"验收结果: {acceptance.verdict.value}（第 {cycle} 轮）",
                        )
                        if (
                            acceptance.verdict == AcceptanceVerdict.PASS
                            and not acceptance.commit_message
                        ):
                            text = lead.send(
                                "ACCEPTANCE pass 缺少 COMMIT_MESSAGE，请补全后重新输出。"
                            )
                            continue
                        return acceptance
                    break
                if cycle == MAX_ACCEPTANCE_CYCLES:
                    break
        raise RuntimeError("主程验收未产出有效 ACCEPTANCE")

    def _log_git_operation(self, tag: str, log: str) -> None:
        print(log)
        if self._run_logger is not None:
            self._run_logger.log_role(tag, log)

    def _lead_reply_after_git_clean(
        self,
        lead: AgentSession,
        text: str,
        *,
        clean_reason: str,
        retry_prompt: str,
    ) -> str:
        if not has_git_clean_request(text):
            return text
        self._apply_git_clean(clean_reason)
        return lead.send(retry_prompt)

    def _advance_after_redo(
        self,
        *,
        requirements: str,
        design: str,
        feedback: str,
        design_revision: str | None,
        clean_reason: str,
        redo_count: int,
        executor_index: int,
    ) -> tuple[int, str, int] | None:
        redo_count += 1
        if redo_count > MAX_REDO_CYCLES:
            self._log("系统", f"已达最大重做次数 ({MAX_REDO_CYCLES})，流程终止。")
            return None
        self._close_executor()
        self._apply_git_clean(clean_reason)
        if design_revision:
            design = design_revision
        else:
            design = self._phase_design_revision(requirements, design, feedback)
        executor_index += 1
        self._log("系统", f"已 git clean，交由执行程序 #{executor_index}（新上下文）")
        return executor_index, design, redo_count

    def _git_commit_and_push(self, commit_message: str | None) -> None:
        if not commit_message or not commit_message.strip():
            raise RuntimeError("验收通过但缺少 COMMIT_MESSAGE")
        self._log("系统", "验收通过，正在 git commit & push...")
        self._log_git_operation(
            "系统/git commit",
            git_commit_all(self.project_root, commit_message.strip()),
        )
        self._log_git_operation("系统/git push", git_push(self.project_root))

    def _apply_git_clean(self, reason: str) -> None:
        self._log("系统", f"git clean（{reason}）...")
        self._log_git_operation("系统/git clean", git_clean_worktree(self.project_root))

    def _run_autotest(self) -> tuple[bool, str]:
        self._log("系统", "运行全量自动化测试...")
        batch = self.project_root / ".engine-test-full.bat"
        result = subprocess.run(
            [str(batch), "--headless"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            shell=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if self._run_logger is not None:
            status = "通过" if result.returncode == 0 else "失败"
            self._run_logger.log_role(f"系统/测试/{status}", output)
        return result.returncode == 0, output
