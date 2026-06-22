"""用户↔主程(需求+设计)→实现→审查 流水线编排。"""

import os
import subprocess
import sys
from pathlib import Path

from cursor_sdk import Client

from agent_session import AgentSession, load_role_prompt, print_role
from config import (
    MAX_EXECUTOR_ROUNDS,
    MAX_REDO_CYCLES,
    MAX_REVIEW_CYCLES,
    PROJECT_ROOT,
)
from git_ops import git_clean_worktree
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
    ) -> None:
        self.client = client
        self.project_root = project_root
        self.api_key = os.environ.get("CURSOR_API_KEY")
        self._executor: AgentSession | None = None
        self._executor_index = 0
        if not self.api_key:
            print("请设置环境变量 CURSOR_API_KEY", file=sys.stderr)
            sys.exit(1)

    def _executor_tag(self) -> str:
        return f"executor#{self._executor_index}"

    def _close_executor(self) -> None:
        if self._executor is not None:
            self._executor.close()
            self._executor = None

    def _open_executor(self, executor_index: int) -> AgentSession:
        self._close_executor()
        self._executor_index = executor_index
        self._executor = AgentSession(
            "executor",
            load_role_prompt("executor"),
            console_tag=self._executor_tag(),
            client=self.client,
            mode="agent",
            api_key=self.api_key,
            cwd=self.project_root,
        )
        return self._executor

    def _run_executor_until_tests_pass(self, initial_message: str) -> None:
        if self._executor is None:
            raise RuntimeError("执行程序会话未打开")
        label = self._executor_tag()
        message = initial_message
        for round_index in range(1, MAX_EXECUTOR_ROUNDS + 1):
            text = self._executor.send(message)
            if has_git_clean_request(text):
                self._apply_git_clean(f"{label} 请求重做")
                message = "工作区已 git clean。请重新实现。"
                continue
            if has_executor_done(text):
                passed, output = self._run_autotest()
                if passed:
                    print_role("系统", f"{label} 全量测试通过。")
                    return
                message = (
                    f"编排器全量测试未通过（第 {round_index} 轮），请修复：\n\n{output}"
                )
                continue
            message = (
                "未检测到 EXECUTOR_DONE。请继续实现，或完成后输出 EXECUTOR_DONE 块。"
            )
        raise RuntimeError(f"{label} 超过最大轮次 ({MAX_EXECUTOR_ROUNDS})")

    def run(self) -> None:
        print("=== Dev Loop ===")
        print(f"项目: {self.project_root}")
        print("主程: 输入「对齐」确认需求并出方案，「退出」结束\n")
        try:
            self._run_pipeline()
        finally:
            self._close_executor()

    def _run_pipeline(self) -> None:
        intake = self._phase_intake()
        if intake is None:
            return
        requirements, design = intake
        executor_index = 1
        redo_count = 0
        need_execute = True

        while True:
            if need_execute:
                self._phase_execute(requirements, design, executor_index)
                need_execute = False

            review = self._phase_review(requirements, design, executor_index)
            if review.verdict == ReviewVerdict.PASS:
                print_role("系统", "审查通过，流程结束。")
                return

            if review.verdict == ReviewVerdict.FIX:
                self._phase_execute_fix(requirements, design, review.feedback)
                continue

            redo_count += 1
            if redo_count > MAX_REDO_CYCLES:
                print_role("系统", f"已达最大重做次数 ({MAX_REDO_CYCLES})，流程终止。")
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
            print_role("系统", f"已 git clean，交由执行程序 #{executor_index}（新上下文）")

    def _phase_intake(self) -> tuple[str, str] | None:
        lead_prompt = load_role_prompt("lead")
        with AgentSession(
            "lead",
            lead_prompt,
            client=self.client,
            mode="plan",
            api_key=self.api_key,
            cwd=self.project_root,
            echo_plan=True,
        ) as lead:
            while True:
                user_input = input("你> ").strip()
                if not user_input:
                    continue
                if user_input in ("退出", "quit", "exit"):
                    return None
                if user_input in ("对齐", "/align"):
                    text = lead.send(
                        "用户已确认对齐。请输出最终需求文档（REQUIREMENTS 块）。"
                    )
                    requirements = extract_block(text, "REQUIREMENTS")
                    if not requirements:
                        print_role(
                            "系统",
                            "未解析到 REQUIREMENTS，请继续与主程澄清或再输入「对齐」。",
                        )
                        continue
                    print_role("系统", "需求已对齐，主程输出技术方案...")
                    text = lead.send("请基于已对齐需求输出技术方案（DESIGN 块）。")
                    design = extract_block(text, "DESIGN")
                    if not design:
                        print_role("系统", "未解析到 DESIGN，请让主程补充或再输入「对齐」。")
                        continue
                    return requirements, design
                lead.send(user_input)

    def _phase_design_revision(
        self, requirements: str, design: str, feedback: str
    ) -> str:
        lead_prompt = load_role_prompt("lead")
        with AgentSession(
            "lead",
            lead_prompt,
            client=self.client,
            mode="plan",
            api_key=self.api_key,
            cwd=self.project_root,
            echo_plan=True,
        ) as lead:
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
        self._open_executor(executor_index)
        task = (
            f"需求：\n{requirements}\n\n方案：\n{design}\n\n"
            "请实现并编写/更新自动化测试，完成后输出 EXECUTOR_DONE。"
        )
        self._run_executor_until_tests_pass(task)

    def _phase_execute_fix(
        self,
        requirements: str,
        design: str,
        feedback: str,
    ) -> None:
        if self._executor is None:
            raise RuntimeError("fix 需要原执行程序会话，但会话已关闭")
        message = (
            f"主程审查要求修复（verdict=fix）：\n{feedback}\n\n"
            f"需求：\n{requirements}\n\n方案：\n{design}\n\n"
            "请小步修改，完成后输出 EXECUTOR_DONE。"
        )
        self._run_executor_until_tests_pass(message)

    def _phase_review(
        self, requirements: str, design: str, executor_index: int
    ):
        lead_prompt = load_role_prompt("lead")
        with AgentSession(
            "lead",
            lead_prompt,
            client=self.client,
            mode="plan",
            api_key=self.api_key,
            cwd=self.project_root,
            echo_plan=True,
        ) as lead:
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
                    print_role(
                        "系统",
                        f"审查结果: {review.verdict.value}（第 {cycle} 轮）",
                    )
                    return review
                if cycle == MAX_REVIEW_CYCLES:
                    raise RuntimeError("主程审查未产出有效 REVIEW")
            raise RuntimeError("unreachable")

    def _apply_git_clean(self, reason: str) -> None:
        print_role("系统", f"git clean（{reason}）...")
        log = git_clean_worktree(self.project_root)
        print(log)

    def _run_autotest(self) -> tuple[bool, str]:
        print_role("系统", "运行全量自动化测试...")
        batch = self.project_root / ".engine-test-full.bat"
        result = subprocess.run(
            [str(batch), "--headless"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            shell=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output
