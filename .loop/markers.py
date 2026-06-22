"""解析 agent 输出中的结构化标记。"""

import re
from dataclasses import dataclass
from enum import Enum


class ReviewVerdict(Enum):
    PASS = "pass"
    FIX = "fix"
    REDO = "redo"


@dataclass
class ReviewResult:
    verdict: ReviewVerdict
    feedback: str
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


def parse_review(text: str) -> ReviewResult | None:
    match = re.search(
        r"<<<REVIEW\s+verdict=[\"']?(pass|fix|redo)[\"']?>>>\s*(.*?)\s*<<<END>>>",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return None
    verdict = ReviewVerdict(match.group(1).lower())
    body = match.group(2).strip()
    design_revision = None
    revision_match = re.search(
        r"<<<DESIGN_REVISION>>>\s*(.*?)(?=<<<END>>>|\Z)",
        body,
        re.DOTALL,
    )
    if revision_match:
        design_revision = revision_match.group(1).strip()
        feedback = body[: revision_match.start()].strip()
    else:
        feedback = body
    return ReviewResult(
        verdict=verdict,
        feedback=feedback,
        design_revision=design_revision,
    )
