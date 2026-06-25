"""C# 源文件文本解析：大纲输出。"""

from __future__ import annotations

import re

NAMESPACE_RE = re.compile(r"^\s*namespace\s+([\w.]+)\s*(?:;|\{)?\s*$")
_MODIFIER = (
    r"(?:public|private|protected|internal|static|sealed|partial|abstract|readonly|unsafe|new)"
)
_TYPE_KIND = r"(?:class|struct|interface|enum|record)"
TYPE_RE = re.compile(
    rf"^\s*(?:{_MODIFIER}\s+)*"
    rf"(?:file\s+)?(?:static\s+)?{_TYPE_KIND}\s+([\w.]+)"
)
REGION_RE = re.compile(r"^\s*#region\s+(.*)")
_MEMBER_MODIFIER = (
    r"(?:public|private|protected|internal|static|sealed|partial|abstract|readonly|"
    r"unsafe|virtual|override|async|new|extern|volatile|const|event)"
)
MEMBER_START_RE = re.compile(
    r"^\s*(?:\[[^\]]+\]\s*)*"
    rf"(?:{_MEMBER_MODIFIER}\s+)*"
    r"(?:[\w.<>,\[\]?]+\s+)+[\w.]+\s*(?:\(|[{;=]|=>)"
)
KEYWORDS = frozenset(
    {
        "if",
        "while",
        "for",
        "foreach",
        "switch",
        "catch",
        "lock",
        "using",
        "return",
        "typeof",
        "sizeof",
        "nameof",
        "new",
        "throw",
        "else",
        "try",
        "do",
        "fixed",
        "checked",
        "unchecked",
    }
)


def strip_line_comment(line: str) -> str:
    """移除行尾 // 注释，保留字符串字面量内的 //。"""
    in_string = False
    escape = False
    for index, char in enumerate(line):
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string and char == "/" and index + 1 < len(line) and line[index + 1] == "/":
            return line[:index].rstrip()
    return line.rstrip()


def count_braces(line: str) -> tuple[int, int]:
    """统计一行中字符串外的 { 与 } 数量。"""
    in_string = False
    escape = False
    opens = 0
    closes = 0
    for char in line:
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            opens += 1
        elif char == "}":
            closes += 1
    return opens, closes


def opens_block(line: str) -> bool:
    """判断该行是否净开启一个代码块。"""
    opens, closes = count_braces(line)
    return opens > closes


def declaration_before_brace(line: str) -> str:
    """提取 { 之前的声明文本并压缩空白。"""
    return re.sub(r"\s+", " ", line.split("{", 1)[0].strip())


def is_member_start(stripped: str) -> bool:
    """判断去注释后的行是否可能是类型成员声明。"""
    if not stripped or stripped in {"{", "}"}:
        return False
    if stripped.startswith("[") or stripped.startswith("using "):
        return False
    region = REGION_RE.match(stripped)
    if region:
        return True
    if stripped.startswith("#") and not region:
        return False
    first = stripped.split(None, 1)[0]
    if first in KEYWORDS:
        return False
    return bool(MEMBER_START_RE.match(stripped))


def balance_depth(text: str) -> tuple[int, int]:
    """返回文本中圆括号与尖括号的嵌套深度。"""
    paren = 0
    angle = 0
    in_string = False
    escape = False
    for char in text:
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "(":
            paren += 1
        elif char == ")":
            paren -= 1
        elif char == "<":
            angle += 1
        elif char == ">":
            angle -= 1
    return paren, angle


def format_signature(signature: str) -> str:
    """规范化成员签名的空白与标点间距。"""
    text = re.sub(r"\s+", " ", signature.strip())
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    return text


def looks_like_member(signature: str) -> bool:
    """判断签名是否像成员声明而非控制流关键字。"""
    match = re.search(r"(\w+)\s*[\(<{;=]", signature)
    if not match:
        return False
    return match.group(1) not in KEYWORDS


def read_member_signature(lines: list[str], start: int) -> tuple[str, int] | None:
    """从 start 行起读取完整成员签名，返回 (签名, 下一行索引)。"""
    stripped = strip_line_comment(lines[start]).strip()
    if not is_member_start(stripped):
        return None

    region = REGION_RE.match(stripped)
    if region:
        return f"#region {region.group(1).strip()}", start + 1

    parts: list[str] = []
    index = start
    while index < len(lines):
        part = strip_line_comment(lines[index]).strip()
        if not part and index > start:
            index += 1
            continue
        parts.append(part)
        combined = " ".join(parts)
        paren, angle = balance_depth(combined)

        if ";" in part and paren <= 0 and angle <= 0:
            signature = format_signature(combined.split(";", 1)[0]) + ";"
            if looks_like_member(signature):
                return signature, index + 1
            return None

        if "{" in combined and paren <= 0 and angle <= 0:
            signature = format_signature(declaration_before_brace(combined))
            if looks_like_member(signature):
                return signature + ";", index + 1
            return None

        if paren <= 0 and angle <= 0 and ")" in combined:
            next_index = index + 1
            while next_index < len(lines) and not strip_line_comment(lines[next_index]).strip():
                next_index += 1
            if next_index < len(lines) and strip_line_comment(lines[next_index]).strip() == "{":
                signature = format_signature(combined)
                if looks_like_member(signature):
                    return signature + ";", next_index + 1

        index += 1
        if index - start > 24:
            break

    return None


def outline_cs_text(lines: list[str]) -> str:
    """扫描 C# 源码行并返回 namespace / 类型 / 成员大纲文本。"""
    output_lines = ["行尾的尖括号表示行号"]
    block_depths: list[int] = []
    brace_depth = 0
    pending_type_block = False
    line_index = 0

    while line_index < len(lines):
        raw_line = lines[line_index]
        line = strip_line_comment(raw_line)
        stripped = line.strip()
        if not stripped:
            line_index += 1
            continue

        opens, closes = count_braces(line)
        at_depth = brace_depth
        out_indent = len(block_depths)

        line_no = line_index + 1
        namespace_match = NAMESPACE_RE.match(stripped)
        if namespace_match:
            output_lines.append(
                "\t" * out_indent + f"namespace {namespace_match.group(1)} <{line_no}>"
            )
            if opens_block(line):
                output_lines.append("\t" * out_indent + "{")
                block_depths.append(at_depth + opens)
            brace_depth += opens - closes
            line_index += 1
            continue

        type_match = TYPE_RE.match(stripped)
        if type_match:
            output_lines.append(
                "\t" * out_indent + f"{declaration_before_brace(stripped)} <{line_no}>"
            )
            if opens_block(line):
                output_lines.append("\t" * out_indent + "{")
                block_depths.append(at_depth + opens)
                pending_type_block = False
            else:
                pending_type_block = True
            brace_depth += opens - closes
            line_index += 1
            continue

        if pending_type_block and stripped == "{":
            output_lines.append("\t" * out_indent + "{")
            block_depths.append(at_depth + 1)
            pending_type_block = False
            brace_depth += opens - closes
            line_index += 1
            continue

        pending_type_block = False

        if block_depths and at_depth == block_depths[-1]:
            member = read_member_signature(lines, line_index)
            if member:
                signature, next_index = member
                output_lines.append("\t" * out_indent + f"{signature} <{line_no}>")
                skipped_opens = 0
                skipped_closes = 0
                for skipped in range(line_index, next_index):
                    open_count, close_count = count_braces(strip_line_comment(lines[skipped]))
                    skipped_opens += open_count
                    skipped_closes += close_count
                brace_depth += skipped_opens - skipped_closes
                line_index = next_index
                while block_depths and brace_depth < block_depths[-1]:
                    block_depths.pop()
                    out_indent = len(block_depths)
                    output_lines.append("\t" * out_indent + "}")
                continue

        brace_depth += opens - closes
        line_index += 1

        while block_depths and brace_depth < block_depths[-1]:
            block_depths.pop()
            output_lines.append("\t" * len(block_depths) + "}")

    return "\n".join(output_lines)
