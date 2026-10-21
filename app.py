"""
Web client-server cho bai tap lon.  Chay:  python app.py   roi mo http://127.0.0.1:5000
Server (Flask) doc cac file ket qua trong data/ va plots/ do cac buoc truoc tao ra, tra ve JSON/anh;
trinh duyet (client) goi API bang fetch() va ve giao dien.
"""
import json
import threading
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                      # phai dat truoc khi import radarChartPlot
import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request, send_from_directory

import radarChartPlot as rc
from backend import price_model as pm

ROOT = Path(__file__).resolve().parent
DATA, PLOTS = ROOT / "data", ROOT / "plots"
app = Flask(__name__)
radar_lock = threading.Lock()              # matplotlib khong an toan khi nhieu luong cung ve

TABLE_COLS = ["Name", "Brand", "Year", "Display_inch", "RAM_GB", "Storage_GB", "Battery_mAh",
              "MainCam_MP", "Weight_g", "Price_EUR", "Price_VND", "Cluster"]
PREDICT_FIELDS = ["RAM_GB", "Storage_GB", "Battery_mAh", "MainCam_MP", "Chipset_nm", "Charge_W",
                  "Wireless_W", "Display_inch", "Weight_g", "Refresh_Hz"]
NOT_ATTR = {"Year", "Cluster", "Price_VND", "ListPrice_VND"}
HINTS = {"results.csv": "Chua co data/results.csv (chay merge_data.py).",
         "top3.csv": "Chua co ket qua phan II. Chay: python backend/stats.py",
         "results2.csv": "Chua co ket qua phan II. Chay: python backend/stats.py",
         "clusters.csv": "Chua co ket qua phan III. Chay: python backend/ml.py",
         "cluster_profile.csv": "Chua co ket qua phan III. Chay: python backend/ml.py"}


class Missing(Exception):
    pass


@app.errorhandler(Missing)
def on_missing(e):
    return jsonify(error=str(e)), 404


def read(name, **kw):
    p = DATA / name
    if not p.exists():
        raise Missing(HINTS.get(name, f"Thieu file data/{name}"))
    return pd.read_csv(p, **kw)


def records(df):
    return json.loads(df.to_json(orient="records", force_ascii=False))   # NaN -> null


def phones_df():
    name = "results_price.csv" if (DATA / "results_price.csv").exists() else "results.csv"
    df = read(name, na_values=["N/a"])
    if (DATA / "clusters.csv").exists():
        cl = pd.read_csv(DATA / "clusters.csv")[["Name", "Cluster"]].drop_duplicates("Name")
        df = df.merge(cl, on="Name", how="left")
    return df


def best_model_row():
    p = DATA / "price_model_report.csv"
    if not p.exists():
        return None
    rep = pd.read_csv(p).iloc[1:]           # bo dong 'Dummy'
    return rep.sort_values("R2_log", ascending=False).iloc[0]


# ---------- Trang chu & anh ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/plots/<path:filename>")
def plots(filename):
    return send_from_directory(PLOTS, filename)


@app.route("/api/health")
def health():
    return jsonify(status="ok")


# ---------- API ----------
@app.get("/api/meta")
def meta():
    df = phones_df()
    attrs = [c for c in df.select_dtypes("number").columns if c not in NOT_ATTR and df[c].notna().mean() >= 0.5]   # bo cot gan nhu trong (AnTuTu, GeekBench)
    stats_attrs = sorted(read("top3.csv")["Attribute"].unique()) if (DATA / "top3.csv").exists() else []
    predict = None
    if pm.MODEL_PATH.exists():
        b = joblib.load(pm.MODEL_PATH)
        fields = []
        for c in PREDICT_FIELDS:
            if c in b["specs"] and c in df:
                s = df[c].dropna()
                fields.append({"name": c, "default": round(float(s.median()), 2),
                               "min": float(s.min()), "max": float(s.max())})
        predict = {"fields": fields, "brands": [f[6:] for f in b["features"] if f.startswith("Brand_")]}
    return jsonify(brands=sorted(df["Brand"].unique()), names=df["Name"].tolist(),
                   table_cols=[c for c in TABLE_COLS if c in df], attrs=attrs,
                   stats_attrs=stats_attrs, predict=predict, n_phones=len(df))


@app.get("/api/phones")
def phones_api():
    df = phones_df()
    return jsonify(records(df[[c for c in TABLE_COLS if c in df]]))


@app.get("/api/stats")
def stats_api():
    attr = request.args.get("attr", "")
    top3 = read("top3.csv")
    if attr not in set(top3["Attribute"]):
        return jsonify(error=f"Khong co thong ke '{attr}'."), 400
    res2 = read("results2.csv", index_col=0)
    summ = res2[["Brand", f"Median of {attr}", f"Mean of {attr}", f"Std of {attr}"]]
    summ.columns = ["Brand", "Median", "Mean", "Std"]
    t = top3[top3["Attribute"] == attr]
    best = None
    if (DATA / "best_brand.csv").exists():
        b = pd.read_csv(DATA / "best_brand.csv")
        b = b[b["Attribute"] == attr]
        best = records(b)[0] if len(b) else None
    img = lambda sub: f"/plots/{sub}/{attr}.png" if (PLOTS / sub / f"{attr}.png").exists() else None
    return jsonify(summary=records(summ), highest=records(t[t["Type"] == "Highest"][["Rank", "Name", "Brand", "Value"]]),
                   lowest=records(t[t["Type"] == "Lowest"][["Rank", "Name", "Brand", "Value"]]),
                   best=best, hist_all=img("all"), hist_brand=img("by_brand"))


@app.get("/api/clusters")
def clusters_api():
    cl = read("clusters.csv")
    prof = read("cluster_profile.csv")
    keep = [c for c in ["Cluster", "So_may", "Battery_mAh", "RAM_GB", "Weight_g", "MainCam_MP", "Price_EUR"] if c in prof]
    cross = pd.crosstab(cl["Cluster"], cl["Brand"]).reset_index()
    return jsonify(points=records(cl), profile=records(prof[keep]), by_brand=records(cross),
                   k=int(cl["Cluster"].nunique()),
                   elbow=("/plots/kmeans_choose_k.png" if (PLOTS / "kmeans_choose_k.png").exists() else None),
                   pca_img=("/plots/pca_clusters.png" if (PLOTS / "pca_clusters.png").exists() else None))


@app.get("/api/radar")
def radar_api():
    p1, p2 = request.args.get("p1", "").strip(), request.args.get("p2", "").strip()
    attrs = [a.strip() for a in request.args.get("attrs", "").split(",") if a.strip()]
    if not p1 or not p2 or len(attrs) < 3:
        return jsonify(error="Hay nhap 2 may va chon it nhat 3 thuoc tinh."), 400
    try:
        with radar_lock:
            out = rc.make_radar(p1, p2, attrs, show=False)
            df = rc.load()
            r1, r2 = rc.find_phone(df, p1), rc.find_phone(df, p2)
    except SystemExit as e:                 # radarChartPlot bao loi bang SystemExit(thong bao)
        return jsonify(error=str(e)), 400
    val = lambda x: None if pd.isna(x) else float(x)
    return jsonify(image="/plots/" + out.relative_to(PLOTS).as_posix(), names=[r1["Name"], r2["Name"]],
                   rows=[{"attr": a, "v1": val(r1[a]), "v2": val(r2[a])} for a in attrs])


@app.post("/api/predict")
def predict_api():
    if not pm.MODEL_PATH.exists():
        return jsonify(error="Chua co mo hinh. Chay: python backend/price_model.py"), 404
    body = request.get_json(force=True, silent=True) or {}
    if not body.get("brand"):
        return jsonify(error="Hay chon hang."), 400
    specs = {}
    for k, v in (body.get("specs") or {}).items():
        try:
            specs[k] = float(v)
        except (TypeError, ValueError):
            pass                            # o trong -> mo hinh dung trung vi
    eur = pm.predict_price(body.get("brand", ""), specs)
    row = best_model_row()
    ape = float(row["Median_APE_%"]) if row is not None else None
    ratio = None
    if (DATA / "results_price.csv").exists():
        d = pd.read_csv(DATA / "results_price.csv", na_values=["N/a"]).dropna(subset=["Price_EUR", "Price_VND"])
        if len(d) >= 10:
            ratio = float((d["Price_VND"] / d["Price_EUR"]).median())
    return jsonify(eur=round(eur), ape=ape, model=None if row is None else row["Model"],
                   low=None if ape is None else round(eur * (1 - ape / 100)),
                   high=None if ape is None else round(eur * (1 + ape / 100)),
                   vnd=None if ratio is None else round(eur * ratio, -4), ratio=ratio)


if __name__ == "__main__":
    app.run(debug=True)