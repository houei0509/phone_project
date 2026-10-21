"""
Phan IV: De xuat + danh gia phuong phap UOC LUONG GIA dien thoai tu thong so.
    python backend/price_model.py
Y tuong:
  * Muc tieu: log(Price_EUR) cua GSMArena (~160 may, du 6 hang). Dung log vi gia lech phai rat manh.
  * Dac trung: cac thong so so (nhu K-means) + hang (one-hot). O trong -> trung vi cua cot.
  * So sanh: Dummy (luon doan trung vi) - Ridge - Random Forest - Gradient Boosting bang 5-fold cross-validation.
  * Kiem tra DOC LAP bang gia ban le VND o CellphoneS (cac may da ghep ten): so du doan (khong thay may do
    luc huan luyen, nho cross_val_predict) voi gia VND thuc te.
Ghi ra: data/price_model_report.csv, data/price_predictions.csv, data/price_model.joblib,
        plots/price_pred_vs_actual.png, plots/price_feature_importance.png
"""
from pathlib import Path
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA, PLOTS = ROOT / "data", ROOT / "plots"
MODEL_PATH = DATA / "price_model.joblib"
EXCLUDE = {"Year", "Price_EUR", "Price_VND", "ListPrice_VND"}
MIN_FILLED = 0.5


def load():
    df = pd.read_csv(DATA / "results_price.csv", na_values=["N/a"])
    num = df.select_dtypes("number").columns
    specs = [c for c in num if c not in EXCLUDE and df[c].notna().mean() >= MIN_FILLED]
    X = pd.concat([df[specs], pd.get_dummies(df["Brand"], prefix="Brand", dtype=float)], axis=1)
    return df, X, specs


def models():
    imp = lambda: SimpleImputer(strategy="median")
    return {
        "Dummy (doan trung vi)": make_pipeline(imp(), DummyRegressor(strategy="median")),
        "Ridge": make_pipeline(imp(), StandardScaler(), Ridge(alpha=10)),
        "Random Forest": make_pipeline(imp(), RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=42)),
        "Gradient Boosting": make_pipeline(imp(), GradientBoostingRegressor(n_estimators=200, max_depth=2,
                                                                          learning_rate=0.05, subsample=0.8, random_state=42)),
    }


def predict_price(brand, specs, model_path=MODEL_PATH):
    """Dung cho web: brand = 'Samsung', specs = {'RAM_GB': 8, 'Battery_mAh': 5000, ...} (thieu thi de trong). Tra ve EUR."""
    b = joblib.load(model_path)
    row = {c: specs.get(c, np.nan) for c in b["specs"]}
    for c in b["features"]:
        if c.startswith("Brand_"):
            row[c] = 1.0 if c == f"Brand_{brand}" else 0.0
    return float(np.exp(b["model"].predict(pd.DataFrame([row])[b["features"]]))[0])


def main():
    df, X, specs = load()
    tr = df["Price_EUR"].notna().values
    Xtr, eur = X[tr], df.loc[tr, "Price_EUR"].values
    y = np.log(eur)
    print(f"Huan luyen tren {tr.sum()}/{len(df)} may co Price_EUR; {len(specs)} thong so + {X.shape[1]-len(specs)} cot hang.\n")

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    rows, oof = [], {}
    for name, mdl in models().items():
        p = cross_val_predict(mdl, Xtr, y, cv=kf)
        oof[name] = p
        ape = np.abs(np.exp(p) - eur) / eur
        rows.append({"Model": name, "R2_log": round(r2_score(y, p), 3),
                     "MAPE_%": round(ape.mean() * 100, 1), "Median_APE_%": round(np.median(ape) * 100, 1)})
    rep = pd.DataFrame(rows)
    rep.to_csv(DATA / "price_model_report.csv", index=False, encoding="utf-8-sig")
    print("So sanh mo hinh (5-fold cross-validation):")
    print(rep.to_string(index=False))

    best = rep[rep["Model"] != rep.iloc[0]["Model"]].sort_values("R2_log", ascending=False).iloc[0]["Model"]
    print(f"\n==> Chon: {best}")
    final = models()[best].fit(Xtr, y)
    joblib.dump({"model": final, "features": list(X.columns), "specs": specs}, MODEL_PATH)

    # Do quan trong cua dac trung (Random Forest fit tren toan bo du lieu)
    rf = models()["Random Forest"].fit(Xtr, y)
    imp = pd.Series(rf[-1].feature_importances_, index=X.columns).sort_values(ascending=False)
    print("\n10 dac trung quan trong nhat (Random Forest):")
    print((imp.head(10) * 100).round(1).astype(str).add("%").to_string())

    # Kiem tra doc lap bang gia VND
    pred = df.loc[tr, ["Name", "Brand", "Price_EUR", "Price_VND"]].copy()
    pred["Pred_EUR_oof"] = np.exp(oof[best]).round(0)
    both = pred.dropna(subset=["Price_VND"])
    print(f"\n--- Kiem tra bang gia ban le CellphoneS (VND), {len(both)} may ---")
    if len(both) >= 10:
        lg_e, lg_v, lg_p = np.log(both["Price_EUR"]), np.log(both["Price_VND"]), np.log(both["Pred_EUR_oof"])
        rate = (both["Price_VND"] / both["Price_EUR"]).median()
        print(f"Tuong quan log(Price_EUR GSMArena) vs log(Price_VND): {np.corrcoef(lg_e, lg_v)[0,1]:.3f}")
        print(f"Tuong quan log(Gia du doan)         vs log(Price_VND): {np.corrcoef(lg_p, lg_v)[0,1]:.3f}")
        print(f"Ty le VND/EUR trung vi giua hai nguon: {rate:,.0f}")
        ape = np.abs(both["Pred_EUR_oof"] * rate - both["Price_VND"]) / both["Price_VND"]
        print(f"Sai so % trung vi khi quy doi du doan EUR -> VND bang ty le tren: {np.median(ape)*100:.1f}%")
        print("(Luu y: ty le tinh tu chinh cac may nay nen so sai so hoi lac quan; ghi ro trong bao cao)")
    else:
        print("Qua it may co gia VND de kiem tra.")
    pred.to_csv(DATA / "price_predictions.csv", index=False, encoding="utf-8-sig")

    # Bieu do
    PLOTS.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.scatter(pred["Price_EUR"], pred["Pred_EUR_oof"], s=22, color="#4C78A8", alpha=0.7, label="Tat ca may")
    ax.scatter(both["Price_EUR"], both["Pred_EUR_oof"], s=30, color="#F58518", label="May co gia VND")
    lim = [min(eur.min(), pred["Pred_EUR_oof"].min()) * 0.9, max(eur.max(), pred["Pred_EUR_oof"].max()) * 1.1]
    ax.plot(lim, lim, "k--", lw=1)
    ax.set(xscale="log", yscale="log", xlim=lim, ylim=lim, xlabel="Gia thuc (EUR)", ylabel="Gia du doan (EUR, cross-validation)",
           title=f"{best}: du doan vs thuc te")
    ax.legend(); fig.tight_layout(); fig.savefig(PLOTS / "price_pred_vs_actual.png", dpi=110); plt.close(fig)

    top = imp.head(12)[::-1]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(top.index, top.values * 100, color="#F58518")
    ax.set(xlabel="Do quan trong (%)", title="Dac trung anh huong nhieu nhat den gia (Random Forest)")
    fig.tight_layout(); fig.savefig(PLOTS / "price_feature_importance.png", dpi=110); plt.close(fig)
    print("\nDa luu bao cao, du doan, mo hinh (data/) va 2 bieu do (plots/).")


if __name__ == "__main__":
    main()
