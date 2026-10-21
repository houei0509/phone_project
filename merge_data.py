import pandas as pd, glob

files = glob.glob("results_*.csv")
print("Gop cac file:", files)

df = pd.concat(
    [pd.read_csv(f, na_values=["N/a"]) for f in files],
    ignore_index=True,
)
df = df.drop_duplicates(subset="URL").sort_values(["Name", "Year"], ascending=[True, False])

# Loai thiet bi deo (dong ho, vong tay...): rat nhe hoac pin rat nho
bad = (df["Weight_g"] < 100) | (df["Battery_mAh"] < 1500)
print("Loai bo:", df.loc[bad, ["Name", "Brand", "Weight_g", "Battery_mAh"]].to_string(index=False))
df = df[~bad]

# Loai may tinh bang / dong ho con sot lai (vi du iPad)
tablets = df["Name"].str.contains(r"iPad|\bTab\b|\bPad\b|Watch|\bBand\b", case=False, regex=True)
print("Loai may tinh bang/dong ho:", df.loc[tablets, "Name"].tolist())
df = df[~tablets]

# Tan so quet > 240 Hz la tan so PWM (doc nham), dat lai thanh o trong
df.loc[df["Refresh_Hz"] > 240, "Refresh_Hz"] = float("nan")

df.to_csv("data/results.csv", index=False, encoding="utf-8-sig", na_rep="N/a")

print("Tong so may:", len(df))
print(df["Brand"].value_counts())
print("\nSo o trong (N/a) moi cot:")
print(df.isna().sum().sort_values(ascending=False).head(12))