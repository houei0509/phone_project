"""
Phan IV (2/2): Ghep gia CellphoneS (VND) vao bang thong so GSMArena theo ten may.
    python backend/match_prices.py
Doc : data/results.csv, data/prices_cellphones.csv
Ghi : data/results_price.csv  (results + Price_VND, ListPrice_VND)
      data/price_matches.csv  (chi tiet tung may: da ghep voi may nao, hoac goi y de kiem tra tay)

Quy tac: CHI ghep khi ten chuan hoa TRUNG KHOP HOAN TOAN.
Khong ghep gan dung (A07 va A07s, Reno16 va Reno16 F la may khac nhau, gia khac nhau).
May co ten phien ban khu vuc, vi du '(China)', '(India)', khong ghep vi la phien ban khac voi ban ban o Viet Nam.
"""
import difflib
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SUGGEST_MIN = 0.9


def norm(name):
    """Chuan hoa ten: bo dung luong, 5G/4G, tien to 'Apple'/'Xiaomi', chu thua; '+' = 'plus'; bo ky tu dac biet."""
    s = name.lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"sắp về hàng|hàng mới về|chính hãng|vn/a|điện thoại|\|", " ", s)
    s = re.sub(r"\b\d+\s*(gb|tb)\b", " ", s)
    s = re.sub(r"\b[45]g\b", " ", s)
    s = s.replace("+", " plus ")
    s = re.sub(r"^(apple|xiaomi)\s+", "", s.strip())
    return re.sub(r"[^a-z0-9]", "", s)          # 'Fold 8' va 'Fold8' thanh cung 'fold8'


def main():
    res = pd.read_csv(DATA / "results.csv", na_values=["N/a"])
    pr = pd.read_csv(DATA / "prices_cellphones.csv")
    pr["key"] = pr["Name_raw"].map(norm)
    # moi may co nhieu phien ban bo nho / nhieu muc gia -> lay muc re nhat (ban co so)
    base = pr.sort_values("Price_VND").groupby("key", as_index=False).first().set_index("key")
    keys = base.index.tolist()

    rows = []
    for _, r in res.iterrows():
        name = r["Name"]
        row = {"Name": name, "Brand": r["Brand"], "Matched_name": None, "Match": "none",
               "Price_VND": None, "ListPrice_VND": None, "Suggestion": None, "Suggestion_score": None}
        if "(" in name:
            row["Match"] = "regional_variant"
        else:
            k = norm(name)
            if k in base.index:
                row.update(Matched_name=base.loc[k, "Name_raw"], Match="exact",
                           Price_VND=base.loc[k, "Price_VND"], ListPrice_VND=base.loc[k, "ListPrice_VND"])
            else:
                c = difflib.get_close_matches(k, keys, n=1, cutoff=SUGGEST_MIN)
                if c:
                    row["Suggestion"] = base.loc[c[0], "Name_raw"]
                    row["Suggestion_score"] = round(difflib.SequenceMatcher(None, k, c[0]).ratio(), 3)
        rows.append(row)
    m = pd.DataFrame(rows)
    m.to_csv(DATA / "price_matches.csv", index=False, encoding="utf-8-sig")
    out = res.merge(m[["Name", "Price_VND", "ListPrice_VND"]].drop_duplicates("Name"), on="Name", how="left")
    out.to_csv(DATA / "results_price.csv", index=False, encoding="utf-8-sig", na_rep="N/a")

    n = m["Price_VND"].notna().sum()
    print(f"Ghep duoc {n}/{len(m)} may ({n / len(m) * 100:.0f}%)")
    print(m["Match"].value_counts().to_string())
    print("\nTheo hang (so may co gia / tong):")
    print(m.groupby("Brand")["Price_VND"].agg(lambda s: f"{s.notna().sum()}/{len(s)}").to_string())
    sg = m[m["Suggestion"].notna()]
    print(f"\n{len(sg)} may co goi y gan giong (KHONG tu dong ghep, xem price_matches.csv de kiem tra tay)")
    # may CellphoneS co gia nhung khong khop may nao trong GSMArena: de biet ten bi lech o dau
    unused = base[~base.index.isin([norm(x) for x in m.loc[m["Match"] == "exact", "Name"]])]
    print(f"\nCellphoneS co {len(base)} may, {len(unused)} may khong khop. Mot so vi du:")
    print(unused["Name_raw"].head(15).to_string(index=False))


if __name__ == "__main__":
    main()
