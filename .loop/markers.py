"""解析 agent 输出中的结构化标记。"""

import re
from dataclasses import dataclass
from enum import Enum

class Verdict(Enum):
    PASS = "pass"
    FIX = "fix"
    REDO = "redo"


ReviewVerdict = Verdict
AcceptanceVerdict = Verdict

_VERDICT_VALUES = r"[\"']?(pass|fix|redo)[\"']?"
_DESIGN_REVISION_RE = re.compile(
    r"<<<DESIGN_REVISION>>>\s*(.*?)(?=<<<END>>>|\Z)",
    re.DOTALL,
)
_COMMIT_MESSAGE_BLOCK_RE = re.compile(
    r"<<<COMMIT_MESSAGE>>>\s*.*?\s*<<<END>>>",
    re.DOTALL,
)


@dataclass
class ReviewResult:
    verdict: ReviewVerdict
    feedback: str
    design_revision: str | None = None


@dataclass
class AcceptanceResult:
    verdict: AcceptanceVerdict
    feedback: str
    commit_message: str | None = None
    design_revision: str | None = None


def extract_block(text: str, block_name: str) -> str | None:
    pattern = rf"<<<{block_name}>>>\s*(.*?)\s*<<<END>>>"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()


def has_git_clean_request(text: str) -> bool:
    return "<<<GIT_CLEAN>>>" in text


def has_executor_done(text: str) -> bool:
    return "<<<EXECUTOR_DONE>>>" in text


def _parse_verdict_marker(text: str, marker: str) -> tuple[str, str] | None:
    header = re.search(
        rf"<<<{marker}\s+verdict={_VERDICT_VALUES}>>>\s*",
        text,
        re.IGNORECASE,
    )
    if not header:
        return None
    body_start = header.end()
    ends = list(re.finditer(r"<<<END>>>", text[body_start:]))
    if not ends:
        return None
    outer_end = ends[-1]
    body = text[body_start : body_start + outer_end.start()].strip()
    return header.group(1).lower(), body


def _split_verdict_body(
    body: str,
    *,
    include_commit_message: bool,
) -> tuple[str, str | None, str | None]:
    commit_message = (
        extract_block(body, "COMMIT_MESSAGE") if include_commit_message else None
    )
    revision_match = _DESIGN_REVISION_RE.search(body)
    if revision_match:
        design_revision = revision_match.group(1).strip()
        feedback = body[: revision_match.start()].strip()
    else:
        design_revision = None
        feedback = body
    if commit_message is not None:
        feedback = _COMMIT_MESSAGE_BLOCK_RE.sub("", feedback, count=1).strip()
    return feedback, design_revision, commit_message


def parse_review(text: str) -> ReviewResult | None:
    parsed = _parse_verdict_marker(text, "REVIEW")
    if not parsed:
        return None
    feedback, design_revision, _ = _split_verdict_body(
        parsed[1],
        include_commit_message=False,
    )
    return ReviewResult(
        verdict=ReviewVerdict(parsed[0]),
        feedback=feedback,
        design_revision=design_revision,
    )


def parse_acceptance(text: str) -> AcceptanceResult | None:
    parsed = _parse_verdict_marker(text, "ACCEPTANCE")
    if not parsed:
        return None
    feedback, design_revision, commit_message = _split_verdict_body(
        parsed[1],
        include_commit_message=True,
    )
    return AcceptanceResult(
        verdict=AcceptanceVerdict(parsed[0]),
        feedback=feedback,
        commit_message=commit_message,
        design_revision=design_revision,
    )
