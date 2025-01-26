import os

import pandas as pd

scripts_dir = os.path.dirname(os.path.realpath(__file__))
df = pd.read_excel(os.path.join(scripts_dir, "cards.xlsx"), sheet_name="Master")
df = df[~pd.isna(df["name"])]
df.to_json(os.path.join(scripts_dir, "../src/assets/cards.json"), orient="records", indent=2)
