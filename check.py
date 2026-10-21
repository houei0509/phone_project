import pandas as pd
p = pd.read_csv("data/price_predictions.csv")
p["Err_%"] = ((p["Pred_EUR_oof"] - p["Price_EUR"]) / p["Price_EUR"] * 100).round(0)
big = p.reindex(p["Err_%"].abs().sort_values(ascending=False).index).head(10)
print(big[["Name", "Brand", "Price_EUR", "Pred_EUR_oof", "Err_%"]].to_string(index=False))