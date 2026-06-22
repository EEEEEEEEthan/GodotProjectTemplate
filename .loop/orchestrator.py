"""用户↔主程(需求+设计)→实现→优化→全量测试→审查 流水线编排。"""

import subprocess
from contextlib import contextmanager
from pathlib import Path

from cursor_sdk import Client

from agent_session import AgentSession, load_role_prompt, print_role
from config import (
    MAX_EXECUTOR_ROUNDS,
    MAX_REDO_CYCLES,
    MAX_REVIEW_CYCLES,
    PROJECT_ROOT,
    ensure_cursor_api_key_env,
)
from git_ops import git_clean_worktree, git_diff
from loop_log import LoopRunLogger
from markers import (
    ReviewVerdict,
    extract_block,
    has_executor_done,
    has_git_clean_request,
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
            f"主程: 与主程澄清并定稿需求/方案后输入 /execute 开始实现"
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
            if review.verdict == ReviewVerdict.PASS:
                self._log("系统", "审查通过，流程结束。")
                return

            if review.verdict == ReviewVerdict.FIX:
                self._phase_execute_fix(requirements, design, review.feedback)
                continue

            redo_count += 1
            if redo_count > MAX_REDO_CYCLES:
                self._log("系统", f"已达最大重做次数 ({MAX_REDO_CYCLES})，流程终止。")
                return

            self._close_executor()
            self._apply_git_clean("主程要求重做")
            if review.design_revision:
                design = review.design_revision
            else:
                design = self._phase_design_revision(
                    requirements, design, review.feedback
                )
            executor_index += 1
            need_execute = True
            self._log("系统", f"已 git clean，交由执行程序 #{executor_index}（新上下文）")

    def _phase_intake(self) -> tuple[str, str]:
        with self._lead_session() as lead:
            requirements: str | None = None
            design: str | None = None
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
                    if not design:
                        self._log(
                            "系统",
                            "尚无 DESIGN，请继续与主程对话直至其输出方案块。",
                        )
                        continue
                    self._log("系统", "开始实现...")
                    return requirements, design
                text = lead.send(user_input)
                if block := extract_block(text, "REQUIREMENTS"):
                    requirements = block
                if block := extract_block(text, "DESIGN"):
                    design = block

    def _phase_design_revision(
        self, requirements: str, design: str, feedback: str
    ) -> str:
        with self._lead_session() as lead:
            text = lead.send(
                "审查结论为 redo。请修订方案（DESIGN 块），避免下一任执行程序重复犯错。\n\n"
                f"原需求：\n{requirements}\n\n原方案：\n{design}\n\n审查意见：\n{feedback}"
            )
        revised = extract_block(text, "DESIGN")
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
                text = lead.send(prompt)
                if has_git_clean_request(text):
                    self._apply_git_clean("主程审查要求清空工作区")
                    text = lead.send(
                        "工作区已 git clean。请输出 REVIEW 块，verdict=redo，并附 DESIGN_REVISION。"
                    )
                review = parse_review(text)
                if review:
                    self._log(
                        "系统",
                        f"审查结果: {review.verdict.value}（第 {cycle} 轮）",
                    )
                    return review
        raise RuntimeError("主程审查未产出有效 REVIEW")

    def _apply_git_clean(self, reason: str) -> None:
        self._log("系统", f"git clean（{reason}）...")
        log = git_clean_worktree(self.project_root)
        print(log)
        if self._run_logger is not None:
            self._run_logger.log_role("系统/git clean", log)

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
