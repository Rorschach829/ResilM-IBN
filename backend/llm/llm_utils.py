# backend/llm_utils.py
from typing import Optional
from openai import OpenAI
import json
# 初始化 DeepSeek 客户端
# client = OpenAI(
#     api_key="sk-692005762cca46ac9faf28703ae6efe0",
#     base_url="https://api.deepseek.com"
# )

#通义千问api
client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key="sk-b4df94d34cbe4734a39e983ba0690c19",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# client = OpenAI(
#     api_key="ollama",  # 随便写，Ollama 不校验
#     base_url="http://localhost:11434/v1"
# )
import json
import re
from typing import Any, Union

class PureJSONExtractError(ValueError):
    """Raised when we cannot extract/repair a valid JSON object/array from raw text."""
    pass


def extract_pure_json(raw: str) -> Union[dict, list]:
    """
    Extract and deterministically repair JSON from LLM output (no extra LLM call).
    Returns: dict or list (already parsed, NOT a string).
    Raises: PureJSONExtractError with helpful details if still invalid.
    """

    if raw is None:
        raise PureJSONExtractError("raw is None")

    text = raw.strip()
    if not text:
        raise PureJSONExtractError("raw is empty")

    # 1) Remove common markdown fences like ```json ... ```
    text = _strip_code_fences(text)

    # 2) Extract the most likely JSON substring (first {...} or [...] block)
    json_candidate = _extract_first_json_block(text)
    if json_candidate is None:
        raise PureJSONExtractError("No JSON object/array found in raw text")

    # 3) Try strict parse first (fast path: DeepSeek usually lands here)
    try:
        return json.loads(json_candidate)
    except Exception as e1:
        # Continue to deterministic repairs
        pass

    # 4) Deterministic repairs (schema-aware light fixes)
    repaired = json_candidate

    # 4.1 Fix a common links typo: missing '{' before '"src": ...'
    repaired = _fix_missing_left_brace_in_links_objects(repaired)
    repaired = _fix_missing_dst_key_in_links(repaired)
    # 4.2 Balance brackets/braces at the end ONLY (avoid inserting in the middle)
    repaired = _balance_trailing_brackets(repaired)

    # 4.3 Remove trailing commas like {...,} or [...,]
    repaired = _remove_trailing_commas(repaired)


    # 5) Parse again
    try:
        return json.loads(repaired)
    except Exception as e2:
        # Provide a compact debug hint (line/col if available)
        hint = _format_json_error(e2)
        raise PureJSONExtractError(
            "Failed to parse JSON after deterministic repairs. "
            f"Hint: {hint}\n"
            "---- JSON CANDIDATE (original) ----\n"
            f"{_shorten(json_candidate)}\n"
            "---- JSON CANDIDATE (repaired) ----\n"
            f"{_shorten(repaired)}"
        ) from e2


def _strip_code_fences(s: str) -> str:
    # Remove ```json ... ``` or ``` ... ```
    fence = re.compile(r"^\s*```(?:json)?\s*([\s\S]*?)\s*```\s*$", re.IGNORECASE)
    m = fence.match(s)
    return m.group(1).strip() if m else s


# def _extract_first_json_block(s: str) -> str | None:
def _extract_first_json_block(s: str) -> Optional[str]:
    """
    Find the first top-level JSON array/object substring by scanning for the first
    '{' or '[' and then taking a best-effort slice until the matching closing bracket.
    If matching fails, returns substring from first bracket to end (to allow repair).
    """
    start = None
    opener = None
    for i, ch in enumerate(s):
        if ch == '{' or ch == '[':
            start = i
            opener = ch
            break
    if start is None:
        return None

    closer = '}' if opener == '{' else ']'

    depth = 0
    in_str = False
    esc = False
    for j in range(start, len(s)):
        c = s[j]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
            continue
        else:
            if c == '"':
                in_str = True
                continue
            if c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    return s[start:j+1].strip()

    # Not matched; return tail for repair
    return s[start:].strip()


def _fix_missing_left_brace_in_links_objects(s: str) -> str:
    """
    Fix the specific pattern you hit:
      "h23", "dst": "s3"},
    or
      "src": "h23", "dst": "s3"},
    by inserting '{' at the start of that item line when it looks like an object.
    This is intentionally conservative: only triggers inside "links": [ ... ] blocks.
    """
    # Quick exit if no links
    if '"links"' not in s:
        return s

    lines = s.splitlines()
    fixed = []
    in_links = False
    bracket_depth = 0

    for line in lines:
        stripped = line.strip()

        # Detect entering links array
        if not in_links and re.search(r'"links"\s*:\s*\[', stripped):
            in_links = True
            # Count '[' on this line to start depth
            bracket_depth += stripped.count('[') - stripped.count(']')
            fixed.append(line)
            continue

        if in_links:
            bracket_depth += stripped.count('[') - stripped.count(']')

            # Heuristic: a links item line that contains '"dst":' and ends with '},' or '}'
            # but does not start with '{' -> add '{'
            # Also handle the exact bad case:  "h23", "dst": "s3"},
            looks_like_object_fragment = (
                '"dst"' in stripped and
                (stripped.endswith('},') or stripped.endswith('}') or stripped.endswith('},') or stripped.endswith('},'))
            )
            if looks_like_object_fragment and not stripped.lstrip().startswith('{'):
                # If it already starts with a quote (e.g., "h23", "dst"...), prefix '{'
                # Keep indentation
                indent = re.match(r'^(\s*)', line).group(1)
                line = indent + '{' + stripped
            fixed.append(line)

            # Leaving links array when depth <= 0 and we see closing bracket
            if bracket_depth <= 0 and ']' in stripped:
                in_links = False
            continue

        fixed.append(line)

    return "\n".join(fixed)


def _balance_trailing_brackets(s: str) -> str:
    """
    Balance missing closing ']' or '}' by appending them at the end only.
    We respect string literals while counting.
    """
    opens = {'{': 0, '[': 0}
    closes = {'}': 0, ']': 0}

    in_str = False
    esc = False
    for c in s:
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
            continue
        else:
            if c == '"':
                in_str = True
                continue
            if c in opens:
                opens[c] += 1
            elif c in closes:
                closes[c] += 1

    need_curly = max(0, opens['{'] - closes['}'])
    need_square = max(0, opens['['] - closes[']'])

    return s + ('}' * need_curly) + (']' * need_square)


def _remove_trailing_commas(s: str) -> str:
    """
    Remove trailing commas before '}' or ']' (common LLM glitch).
    """
    # Replace ",}" -> "}" and ",]" -> "]" ignoring whitespace/newlines
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)
    return s


def _format_json_error(e: Exception) -> str:
    # json.JSONDecodeError has lineno/colno/msg
    if hasattr(e, "lineno") and hasattr(e, "colno") and hasattr(e, "msg"):
        return f"{e.msg} at line {e.lineno}, col {e.colno}"
    return str(e)


def _shorten(s: str, limit: int = 1200) -> str:
    if len(s) <= limit:
        return s
    return s[:limit] + "\n... (truncated) ...\n"

def _fix_missing_dst_key_in_links(s: str) -> str:
    if '"links"' not in s:
        return s

    lines = s.splitlines()
    fixed = []
    in_links = False
    depth = 0

    for line in lines:
        stripped = line.strip()

        if not in_links and re.search(r'"links"\s*:\s*\[', stripped):
            in_links = True
            depth += stripped.count('[') - stripped.count(']')
            fixed.append(line)
            continue

        if in_links:
            depth += stripped.count('[') - stripped.count(']')

            # Match: {"src": "h16", "s2"},  (second string without key)
            m = re.search(r'^\s*\{\s*"src"\s*:\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\}\s*,?\s*$', line)
            if m:
                indent = re.match(r'^(\s*)', line).group(1)
                comma = ',' if stripped.endswith(',') else ''
                line = f'{indent}{{"src": "{m.group(1)}", "dst": "{m.group(2)}"}}{comma}'

            fixed.append(line)

            if depth <= 0 and ']' in stripped:
                in_links = False
            continue

        fixed.append(line)

    return "\n".join(fixed)
