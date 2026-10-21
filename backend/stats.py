# Phan II: top 3, median/mean/std, histogram. (Lam o buoc sau)
"""
Phan II: thong ke + bieu do.  Chay tu thu muc goc du an:  python backend/stats.py
Sinh ra:
  data/top3.csv        - 3 may cao nhat / thap nhat moi thong ke
  data/results2.csv    - median/mean/std cua tung thong ke: toan bo ('all') va theo tung hang
  data/best_brand.csv  - hang co gia tri trung binh tot nhat moi thong ke
  plots/all/*.png      - histogram toan bo may
  plots/by_brand/*.png - histogram tung hang (luoi nho)
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")                      # ve ra file, khong mo cua so
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA, PLOTS = ROOT / "data", ROOT / "plots"

EXCLUDE = {"Year"}                              # cot so nhung khong phai "thong so ky thuat"
LOWER_BETTER = {"Weight_g", "Thickness_mm", "Chipset_nm", "Price_EUR"}   # cang thap cang tot
NEUTRAL = {"Length_mm", "Width_mm", "Display_inch", "Res_W", "Res_H","CPU_cores"}    # khong co tot/xau ro rang
MIN_FILLED = 0.5                                # bo cot co it hon 50% du lieu


def load():
    df = pd.read_csv(DATA / "results.csv", na_values=["N/a"])
    num = df.select_dtypes("number").columns
    keep = [c for c in num if c not in EXCLUDE and df[c].notna().mean() >= MIN_FILLED]
    dropped = [c for c in num if c not in keep and c not in EXCLUDE]
    if dropped:
        print("Bo cot thieu qua nhieu du lieu:", dropped)
    return df, keep


def top3(df, cols):
    rows = []
    for c in cols:
        d = df.dropna(subset=[c])
        for rank, (_, r) in enumerate(d.nlargest(3, c).iterrows(), 1):
            rows.append({"Attribute": c, "Type": "Highest", "Rank": rank, "Name": r["Name"], "Brand": r["Brand"], "Value": r[c]})
        for rank, (_, r) in enumerate(d.nsmallest(3, c).iterrows(), 1):
            rows.append({"Attribute": c, "Type": "Lowest", "Rank": rank, "Name": r["Name"], "Brand": r["Brand"], "Value": r[c]})
    out = pd.DataFrame(rows)
    out.to_csv(DATA / "top3.csv", index=False, encoding="utf-8-sig")
    return out


def summary_table(df, cols):
    """Hang 'all' + moi hang; moi thong ke co 3 cot Median/Mean/Std."""
    groups = [("all", df)] + [(b, g) for b, g in df.groupby("Brand")]
    rows = []
    for name, g in groups:
        row = {"Brand": name}
        for c in cols:
            row[f"Median of {c}"] = g[c].median()
            row[f"Mean of {c}"] = g[c].mean()
            row[f"Std of {c}"] = g[c].std()
        rows.append(row)
    out = pd.DataFrame(rows).round(3)
    out.to_csv(DATA / "results2.csv", encoding="utf-8-sig", na_rep="N/a")   # co cot index 0..n nhu de bai
    return out


def histograms(df, cols):
    (PLOTS / "all").mkdir(parents=True, exist_ok=True)
    (PLOTS / "by_brand").mkdir(parents=True, exist_ok=True)
    brands = sorted(df["Brand"].unique())
    for c in cols:
        s = df[c].dropna()
        if s.empty:
            continue
        # 1) toan bo may
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(s, bins=20, color="#4C78A8", edgecolor="white")
        ax.set(title=f"{c} - tat ca may (n={len(s)})", xlabel=c, ylabel="So may")
        fig.tight_layout(); fig.savefig(PLOTS / "all" / f"{c}.png", dpi=110); plt.close(fig)
        # 2) tung hang, dung chung bin de so sanh duoc
        bins = np.histogram_bin_edges(s, bins=15)
        ncol = 3
        nrow = int(np.ceil(len(brands) / ncol))
        fig, axes = plt.subplots(nrow, ncol, figsize=(12, 3.2 * nrow), sharex=True)
        for ax, b in zip(axes.flat, brands):
            v = df.loc[df["Brand"] == b, c].dropna()
            ax.hist(v, bins=bins, color="#F58518", edgecolor="white")
            ax.set_title(f"{b} (n={len(v)})", fontsize=10)
        for ax in list(axes.flat)[len(brands):]:
            ax.axis("off")
        fig.suptitle(f"{c} theo hang"); fig.tight_layout()
        fig.savefig(PLOTS / "by_brand" / f"{c}.png", dpi=100); plt.close(fig)


def best_brand(df, cols):
    mean_by_brand = df.groupby("Brand")[cols].mean()
    rows = []
    for c in cols:
        if c in NEUTRAL:
            continue
        b = mean_by_brand[c].idxmin() if c in LOWER_BETTER else mean_by_brand[c].idxmax()
        rows.append({"Attribute": c, "BestBrand": b, "MeanValue": round(mean_by_brand.loc[b, c], 3),
                     "Rule": "lowest" if c in LOWER_BETTER else "highest"})
    out = pd.DataFrame(rows)
    out.to_csv(DATA / "best_brand.csv", index=False, encoding="utf-8-sig")
    return out


def main():
    df, cols = load()
    print(f"{len(df)} may, {len(cols)} thong ke:", cols)
    top3(df, cols)
    summary_table(df, cols)
    histograms(df, cols)
    best = best_brand(df, cols)
    print("\nHang tot nhat theo tung thong ke:")
    print(best.to_string(index=False))
    print("\nSo thong ke ma moi hang dung dau:")
    print(best["BestBrand"].value_counts().to_string())


if __name__ == "__main__":
    main()