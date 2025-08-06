# backend/utils/token_utils.py

total_tokens_used = 0  # 全局变量

def record_tokens_from_response(response):
    global total_tokens_used
    try:
        if hasattr(response, "usage"):
            prompt = response.usage.prompt_tokens
            completion = response.usage.completion_tokens
            total = response.usage.total_tokens
            total_tokens_used += total

            print(f"[Token Monitor] prompt: {prompt}, completion: {completion}, total: {total}")
        else:
            print("[Token Monitor] ⚠️ 无 usage 字段，可能是异常响应")
    except Exception as e:
        print(f"[Token Monitor] ❌ 记录 token 时出错: {e}")

def get_total_tokens():
    global total_tokens_used
    return total_tokens_used

