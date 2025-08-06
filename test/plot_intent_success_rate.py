
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# Load data from CSV
df = pd.read_csv("intent_summary.csv")

# Assign color based on number of hosts
def get_color(hosts):
    if hosts < 4:
        return "green"  # Small topology
    elif hosts < 10:
        return "blue"   # Medium topology
    else:
        return "red"    # Large topology

df["color"] = df["hosts"].apply(get_color)

# Create figure and dual axes
fig, ax1 = plt.subplots(figsize=(10, 6))

# Bar chart for average execution time
bars = ax1.bar(df["intent_id"], df["avg_time"], color=df["color"], label="Avg Time (s)")
ax1.set_xlabel("Intent ID")
ax1.set_ylabel("Average Execution Time (s)", color="black")
ax1.tick_params(axis="y", labelcolor="black")
ax1.set_ylim(0, df["avg_time"].max() * 1.2)
ax1.grid(axis="y", linestyle="--", alpha=0.6)

# Line chart for success rate
ax2 = ax1.twinx()
ax2.plot(df["intent_id"], df["success_rate"], color="black", marker="o", linewidth=2, label="Success Rate (%)")
ax2.set_ylabel("Success Rate (%)", color="black")
ax2.tick_params(axis="y", labelcolor="black")
ax2.set_ylim(0, 110)

# X-axis ticks aligned with bars
plt.xticks(ticks=df["intent_id"], labels=df["intent_id"], fontsize=10)

# Legend outside top-right
legend_elements = [
    Patch(facecolor='green', label='Small Topology (hosts < 4)'),
    Patch(facecolor='blue', label='Medium Topology (4 ≤ hosts < 10)'),
    Patch(facecolor='red', label='Large Topology (hosts ≥ 10)'),
    Patch(facecolor='gray', label='Avg Time (bar)'),
    Patch(facecolor='white', edgecolor='black', label='Success Rate (line)', linewidth=2)
]
plt.legend(handles=legend_elements, loc="upper left", bbox_to_anchor=(1.0, 1.0))

# Title
plt.title("Intent Execution Time and Success Rate by Topology Size")

# Adjust layout to make space for legend
plt.tight_layout(rect=[0, 0, 0.85, 1])

# Save figure
plt.savefig("intent_time_success_combined.png", dpi=300)
print("✅ Chart saved as intent_time_success_combined.png")
