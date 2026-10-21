# Phan III + IV: K-means, PCA, radar, uoc luong gia. (Lam o buoc sau)
"""
Phan III (K-means + PCA).  Chay tu thu muc goc du an:
    python backend/ml.py            # tu chon k theo Silhouette
    python backend/ml.py --k 4      # tu chon k
Sinh ra:
  plots/kmeans_choose_k.png   - Elbow + Silhouette de chon k
  plots/pca_clusters.png      - bieu do 2D (PCA) to mau theo cum
  data/clusters.csv           - moi may thuoc cum nao + toa do PCA
  data/cluster_profile.csv    - gia tri trung binh cua tung cum (de dat ten / nhan xet)
"""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA, PLOTS = ROOT / "data", ROOT / "plots"
# Gia (Price_EUR) de danh cho phan IV; Year khong phai thong so ky thuat
EXCLUDE = {"Year", "Price_EUR"}
MIN_FILLED = 0.5


def load_features():
    df = pd.read_csv(DATA / "results.csv", na_values=["N/a"])
    num = df.select_dtypes("number").columns
    cols = [c for c in num if c not in EXCLUDE and df[c].notna().mean() >= MIN_FILLED]
    X = df[cols].fillna(df[cols].median())            # o trong -> trung vi cua cot
    Xs = StandardScaler().fit_transform(X)            # dua ve cung thang do
    return df, cols, Xs


def choose_k(Xs, k_range=range(2, 11)):
    inertia, sil = [], []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(Xs)
        inertia.append(km.inertia_)
        sil.append(silhouette_score(Xs, km.labels_))
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(list(k_range), inertia, "o-"); ax[0].set(title="Elbow", xlabel="k", ylabel="Inertia")
    ax[1].plot(list(k_range), sil, "o-", color="#F58518"); ax[1].set(title="Silhouette", xlabel="k", ylabel="Score")
    fig.tight_layout(); PLOTS.mkdir(exist_ok=True); fig.savefig(PLOTS / "kmeans_choose_k.png", dpi=110); plt.close(fig)
    table = pd.DataFrame({"k": list(k_range), "inertia": inertia, "silhouette": sil})
    print(table.round(3).to_string(index=False))
    # k tot nhat theo silhouette, nhung chi xet k>=3 de ket qua co y nghia phan tich
    best = table[table["k"] >= 3].sort_values("silhouette", ascending=False).iloc[0]["k"]
    return int(best)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=None)
    args = ap.parse_args()

    df, cols, Xs = load_features()
    print(f"{len(df)} may, {len(cols)} thong ke dung de phan cum:\n{cols}\n")

    k = args.k or choose_k(Xs)
    print(f"\n==> Dung k = {k}")
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(Xs)
    df["Cluster"] = km.labels_

    # PCA 2 chieu
    pca = PCA(n_components=2, random_state=42)
    P = pca.fit_transform(Xs)
    df["PC1"], df["PC2"] = P[:, 0], P[:, 1]
    ev = pca.explained_variance_ratio_
    print(f"PCA giu lai {ev.sum()*100:.1f}% thong tin (PC1 {ev[0]*100:.1f}%, PC2 {ev[1]*100:.1f}%)")

    fig, ax = plt.subplots(figsize=(8, 6))
    sc = ax.scatter(df["PC1"], df["PC2"], c=df["Cluster"], cmap="tab10", s=40, alpha=0.8, edgecolor="white", linewidth=0.5)
    ax.legend(*sc.legend_elements(), title="Cum")
    ax.set(title=f"K-means (k={k}) tren khong gian PCA 2 chieu",
           xlabel=f"PC1 ({ev[0]*100:.1f}%)", ylabel=f"PC2 ({ev[1]*100:.1f}%)")
    fig.tight_layout(); fig.savefig(PLOTS / "pca_clusters.png", dpi=110); plt.close(fig)

    df[["Name", "Brand", "Cluster", "PC1", "PC2"]].round(4).to_csv(DATA / "clusters.csv", index=False, encoding="utf-8-sig")

    # Dac diem tung cum: de nhan xet / dat ten
    profile = df.groupby("Cluster")[cols + ["Price_EUR"]].mean().round(2)
    profile.insert(0, "So_may", df.groupby("Cluster").size())
    profile.to_csv(DATA / "cluster_profile.csv", encoding="utf-8-sig")
    print("\nDac diem trung binh moi cum (xem de dat ten cum):")
    print(profile[["So_may", "Battery_mAh", "RAM_GB", "Weight_g", "MainCam_MP", "Price_EUR"]].to_string()
          if {"Battery_mAh", "RAM_GB", "Weight_g", "MainCam_MP"} <= set(profile.columns) else profile.iloc[:, :8].to_string())
    print("\nSo may theo cum x hang:")
    print(pd.crosstab(df["Cluster"], df["Brand"]).to_string())


if __name__ == "__main__":
    main()