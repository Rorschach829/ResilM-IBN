import pandas as pd

# 读取两个实验数据文件
df1 = pd.read_csv("r1.csv")
df2 = pd.read_csv("r2.csv")

# 校验列结构
if not df1.columns.equals(df2.columns):
    raise ValueError("两个CSV文件的列结构不一致！")

# 假设“轮次”列名为 '轮次'，将 r2 的轮次偏移 +5
df2 = df2.copy()
df2["轮次"] = df2["轮次"] + 5

# 合并两个 DataFrame
merged_df = pd.concat([df1, df2], ignore_index=True)

# 按编号和轮次排序（可选）
merged_df = merged_df.sort_values(by=["编号", "轮次"]).reset_index(drop=True)

# 保存合并结果
merged_df.to_csv("merged_result.csv", index=False, encoding="utf-8-sig")

print("✅ 合并完成，结果保存为 merged_result.csv")
