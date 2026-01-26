import pandas as pd
import math

def format_number(x):
    """
    整数：返回 int
    小数：保留 1 位小数
    """
    if x is None or pd.isna(x):
        return None

    if math.isclose(x, round(x)):
        return int(round(x))
    else:
        return round(x, 1)


def parse_token_value(val):
    """
    单个数字：原样
    a+b+c：取平均
    """
    if pd.isna(val):
        return None

    val = str(val).strip()

    if '+' in val:
        nums = [float(v) for v in val.split('+')]
        avg = sum(nums) / len(nums)
        return format_number(avg)

    return format_number(float(val))


# 读取 CSV
df = pd.read_csv("intent_token.csv")

# 处理两列
df["intent_token_avg"] = df["intent_token"].apply(parse_token_value)
df["json_token_avg"] = df["json_token"].apply(parse_token_value)

# 保存结果
df.to_csv("intent_token_processed.csv", index=False)

print("✅ 处理完成：整数保留整数，小数保留 1 位")