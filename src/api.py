"""
Perfume AI – Dupe Finder & Recommendation API
- Loads perfumes_clean.csv (GBP-normalised prices)
- Builds TF-IDF model from accords+notes
- Exposes /dupes?name=... for similar perfumes
"""
import json

from pathlib import Path
from difflib import get_close_matches
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# -------------------- 1) App setup --------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)  # for dev, allow all origins

# -------------------- 2) Load data --------------------
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "perfumes_clean.csv"
df = pd.read_csv(DATA_PATH)

# Build scent profile text
df["profile_text"] = (
    df["accords"].fillna("") + " " + df["notes"].fillna("")
).str.lower()

# TF-IDF model
vec = TfidfVectorizer(token_pattern=r"[A-Za-zÀ-ÿ']+")
X = vec.fit_transform(df["profile_text"])

# -------------------- 3) Helpers --------------------
def find_index_by_name(query: str):
    """Find index for perfume by name (exact, fuzzy, or partial match)."""
    matches = df.index[df["name"].str.lower() == query.lower()].tolist()
    if matches:
        return matches[0]
    guess = get_close_matches(query, df["name"].tolist(), n=1, cutoff=0.6)
    if guess:
        return df.index[df["name"] == guess[0]][0]
    partial_matches = df[df["name"].str.lower().str.contains(query.lower())]
    if not partial_matches.empty:
        return partial_matches.index[0]
    return None

def recommend(idx, top_k=5, price_cap=None, cheaper_than=True):
    """Return top-k similar perfumes (optionally filtered by price)."""
    sims = cosine_similarity(X[idx], X).flatten()
    out = df.copy()
    out["similarity"] = sims
    out = out[out.index != idx]
    if "price_gbp" in out.columns:
        if price_cap is not None:
            out = out[out["price_gbp"].notna() & (out["price_gbp"] <= price_cap)]
        if cheaper_than and pd.notna(df.loc[idx, "price_gbp"]):
            out = out[out["price_gbp"].notna() & (out["price_gbp"] < df.loc[idx, "price_gbp"])]
    out = out.sort_values("similarity", ascending=False).head(top_k)
    return [
        {
            "name": r["name"],
            "brand": r["brand"],
            "price": float(r["price_gbp"]) if pd.notna(r.get("price_gbp")) else None,
            "similarity": float(r["similarity"]),
        }
        for _, r in out.iterrows()
    ]

# -------------------- 4) Routes --------------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/names")
def names():
    return jsonify(sorted(df["name"].unique().tolist()))

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/dupes")
def dupes():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Missing 'name' parameter."}), 400
    idx = find_index_by_name(name)
    if idx is None:
        return jsonify({"error": f"'{name}' not found"}), 404
    try:
        top_k = int(request.args.get("top_k", 5))
    except ValueError:
        top_k = 5
    cheaper_than = request.args.get("cheaper_than", "true").lower() in ("1", "true", "yes")
    price_cap_raw = request.args.get("price_cap")
    price_cap = float(price_cap_raw) if price_cap_raw else None
    results = recommend(idx, top_k=top_k, price_cap=price_cap, cheaper_than=cheaper_than)
    base = df.loc[idx]
    return jsonify({
        "query": {
            "name": base["name"],
            "brand": base["brand"],
            "price": float(base["price_gbp"]) if pd.notna(base.get("price_gbp")) else None
        },
        "params": {"top_k": top_k, "cheaper_than": cheaper_than, "price_cap": price_cap},
        "results": results
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
