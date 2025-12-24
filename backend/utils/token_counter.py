TOKEN_STATE = {"intent": 0, "json": 0}

def reset():
    TOKEN_STATE["intent"] = 0
    TOKEN_STATE["json"] = 0

def add_intent(n: int):
    if n:
        TOKEN_STATE["intent"] += int(n)

def add_json(n: int):
    if n:
        TOKEN_STATE["json"] += int(n)

def summary():
    return {
        "intent_token": TOKEN_STATE["intent"],
        "json_token": TOKEN_STATE["json"],
        "total_token": TOKEN_STATE["intent"] + TOKEN_STATE["json"],
    }