# python radarChartPlot.py --p1 <ten1> --p2 <ten2> --Attribute a,b,c  (Lam o buoc sau)
"""
Phan III: Bieu do radar so sanh hai dien thoai.
Cu phap:
    python radarChartPlot.py --p1 "Galaxy S24" --p2 "iPhone 15" --Attribute RAM_GB,Battery_mAh,MainCam_MP,Weight_g
Moi truc cua radar = 1 thong so, da chuan hoa ve 0-1 (min-max tren TOAN BO may) de so sanh duoc.
Ten may co the viet khong day du (co the bo ten hang); neu co nhieu may khop thi script se liet ke de ban chon.
"""
import argparse
import difflib
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "results.csv"
OUT_DIR = ROOT / "plots" / "radar"


def load():
    return pd.read_csv(DATA, na_values=["N/a"])


def find_phone(df, query):
    """Tim 1 may theo ten (khong phan biet hoa thuong, co the bo ten hang)."""
    q = query.strip().lower()
    full = df["Name"].str.lower()
    short = pd.Series(
        [n[len(b):].strip() if n.startswith(b.lower()) else n for n, b in zip(full, df["Brand"])],
        index=df.index,
    )
    exact = df[(full == q) | (short == q)]
    if len(exact) >= 1:
        return exact.iloc[0]                    # trung ten -> lay may moi nhat (file da sap xep Year giam dan)
    tokens = q.split()
    cand = df[full.apply(lambda s: all(t in s for t in tokens))]
    if len(cand) == 1:
        return cand.iloc[0]
    if cand.empty:
        close = difflib.get_close_matches(q, full.tolist(), n=5, cutoff=0.4)
        hint = ("\nCo phai ban muon tim: " + "; ".join(df.loc[full.isin(close), "Name"])) if close else ""
        raise SystemExit(f"Khong tim thay may '{query}'.{hint}")
    names = "; ".join(cand["Name"].head(10))
    raise SystemExit(f"'{query}' khop nhieu may, hay ghi ro hon. Cac may khop: {names}")


def make_radar(p1, p2, attrs, out=None, show=False):
    df = load()
    bad = [a for a in attrs if a not in df.columns or not pd.api.types.is_numeric_dtype(df[a])]
    if bad:
        nums = [c for c in df.select_dtypes("number").columns]
        raise SystemExit(f"Thuoc tinh khong hop le: {bad}.\nCac thuoc tinh so co the dung: {', '.join(nums)}")

    r1, r2 = find_phone(df, p1), find_phone(df, p2)

    # bo thuoc tinh ma 1 trong 2 may khong co du lieu
    missing = [a for a in attrs if pd.isna(r1[a]) or pd.isna(r2[a])]
    if missing:
        print("Bo qua (thieu du lieu o it nhat 1 may):", missing)
    attrs = [a for a in attrs if a not in missing]
    if len(attrs) < 3:
        raise SystemExit("Can it nhat 3 thuoc tinh co du lieu de ve radar.")

    lo, hi = df[attrs].min(), df[attrs].max()
    span = (hi - lo).replace(0, np.nan)
    norm = lambda r: ((r[attrs].astype(float) - lo) / span).fillna(0.5).values

    v1, v2 = norm(r1), norm(r2)
    angles = np.linspace(0, 2 * np.pi, len(attrs), endpoint=False)
    closed = lambda v: np.concatenate([v, v[:1]])
    ang = np.concatenate([angles, angles[:1]])

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.plot(ang, closed(v1), color="#4C78A8", linewidth=2, label=r1["Name"])
    ax.fill(ang, closed(v1), color="#4C78A8", alpha=0.2)
    ax.plot(ang, closed(v2), color="#F58518", linewidth=2, label=r2["Name"])
    ax.fill(ang, closed(v2), color="#F58518", alpha=0.2)
    ax.set_xticks(angles)
    ax.set_xticklabels(attrs)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["25%", "50%", "75%", "100%"], fontsize=8, color="gray")
    ax.set_title("So sanh (0-100% = thap nhat-cao nhat trong tat ca may)", fontsize=10, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    fig.tight_layout()

    if out is None:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", f"{r1['Name']}_vs_{r2['Name']}").strip("_")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / f"{slug}.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")

    table = pd.DataFrame({r1["Name"]: r1[attrs].values, r2["Name"]: r2[attrs].values}, index=attrs)
    print(table.to_string())
    print("Da luu:", out)
    if show:
        plt.show()
    plt.close(fig)
    return Path(out)


def main():
    ap = argparse.ArgumentParser(description="Radar chart so sanh 2 dien thoai")
    ap.add_argument("--p1", required=True, help="ten may thu nhat")
    ap.add_argument("--p2", required=True, help="ten may thu hai")
    ap.add_argument("--Attribute", required=True, nargs="+", help="cac thuoc tinh, cach nhau bang dau phay")
    ap.add_argument("--no-show", action="store_true", help="chi luu anh, khong mo cua so")
    args = ap.parse_args()
    attrs = [a.strip() for chunk in args.Attribute for a in chunk.split(",") if a.strip()]
    make_radar(args.p1, args.p2, attrs, show=not args.no_show)


if __name__ == "__main__":
    main()