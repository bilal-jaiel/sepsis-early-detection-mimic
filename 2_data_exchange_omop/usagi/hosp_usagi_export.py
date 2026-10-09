import pandas as pd

df = pd.read_csv("consolidated_uasgi_master.csv", na_values=["NULL"], keep_default_na=True)

df_sorted = df.sort_values(by="frequency", ascending=False)

df_sorted.to_csv(
    "consolidated_uasgi_master_sorted.csv",
    index=False,
    na_rep="NULL"
)

import matplotlib.pyplot as plt

frequency_counts = df_sorted["frequency"].value_counts().sort_index()

plt.figure(figsize=(10, 6))
plt.bar(frequency_counts.index, frequency_counts.values)
plt.xlabel("Frequency")
plt.ylabel("Count")
plt.title("Distribution of Frequency")
plt.xlim(0, 100)
plt.xticks(range(0, 101, 10))
plt.grid(axis="y")
plt.show()

threshold = 10

df_filtered = df_sorted[df_sorted["frequency"] > threshold]

df_filtered.to_csv(
    "consolidated_uasgi_master_filtered.csv",
    index=False,
    na_rep="NULL"
)