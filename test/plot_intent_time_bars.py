import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# Load CSV file
df = pd.read_csv("intent_summary.csv")

# Assign color based on topology size
def get_color(hosts):
    if hosts < 4:
        return "green"  # Small
    elif hosts < 10:
        return "blue"   # Medium
    else:
        return "red"    # Large

df["color"] = df["hosts"].apply(get_color)

# Create bar chart
plt.figure(figsize=(10, 6))
bars = plt.bar(df["intent_id"], df["avg_time"], color=df["color"])

# Fix X-axis ticks: align with bar centers
plt.xticks(ticks=df["intent_id"], labels=df["intent_id"], rotation=0, fontsize=10)

# Axis labels and title
plt.xlabel("Intent ID")
plt.ylabel("Average Execution Time (s)")
plt.title("Average Execution Time by Topology Size")

# Y-axis grid
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Legend
legend_elements = [
    Patch(facecolor='green', label='Small Topology (hosts < 4)'),
    Patch(facecolor='blue', label='Medium Topology (4 ≤ hosts < 10)'),
    Patch(facecolor='red', label='Large Topology (hosts ≥ 10)')
]
plt.legend(handles=legend_elements)

# Save figure
plt.tight_layout()
plt.savefig("avg_time_by_topology.png", dpi=300)
print("✅ Chart saved as avg_time_by_topology.png")

# Show plot (optional)

