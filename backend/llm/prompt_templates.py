# backend/llm/prompt_templates.py

from pathlib import Path

PROMPT_FILE_PATH = Path("/data/gjw/Meta-IBN/backend/agents/prompts/planner_agent.txt")

try:
    PLANNER_SYSTEM_PROMPT = PROMPT_FILE_PATH.read_text(encoding='utf-8')
except Exception as e:
    PLANNER_SYSTEM_PROMPT = "⚠️ [Prompt 加载失败] 请检查 planner_agent.txt 是否存在并可读"
    print(f"[Prompt Load Error] {e}")
