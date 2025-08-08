from pathlib import Path
from flask import Flask, request, jsonify
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import get_close_matches

# ---------- Load data & build model once at startup ----------
DATA_PATH = (Path(__file__).resolve().parent.parent / "data" / "perfumes_sample.csv")

df = pd.read_csv(DATA_PATH)
df["profile_text"] = (df["accords"].fillna("") + " " + df["notes"].fillna("")).str.lower()

vec = TfidfVectorizer(token_pattern=r"[A-Za-zÀ-ÿ']+")
X = vec.fit_transform(df["profile_text"])

def find_index_by_name(query: str):
    matches = df.index[df["name"].str.lower() == query.lower()].tolist()
    if matches:
        return matches[0]
    guess = get_close_matches(query, df["name"].tolist(), n=1, cutoff=0.6)
    if guess:
        return df.index[df["name"] == guess[0]][0]
    return None

def recommend(idx, top_k=5, price_cap=None, cheaper_than=True):
    sims = cosine_similarity(X[idx], X).flatten()
    out = df.copy()
    out["similarity"] = sims
    out = out[out.index != idx]
    if price_cap is not None:
        out = out[out["price"] <= price_cap]
    if cheaper_than:
        out = out[out["price"] < df.loc[idx, "price"]]
    out = out.sort_values("similarity", ascending=False).head(top_k)
    # return a JSON-friendly list of dicts
    return [
        {
            "name": r["name"],
            "brand": r["brand"],
            "price": float(r["price"]),
            "similarity": float(r["similarity"])
        }
        for _, r in out.iterrows()
    ]

# ---------- Flask app ----------
app = Flask(__name__)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/dupes")
def dupes():
    """
    Query params:
      - name (required): perfume name, e.g. Dior Sauvage
      - top_k (optional, int): how many results, default 5
      - cheaper_than (optional, bool): true/false, default true
      - price_cap (optional, float): max price
    """
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Missing 'name' parameter."}), 400

    idx = find_index_by_name(name)
    if idx is None:
        return jsonify({
            "error": f"'{name}' not found",
            "try": sorted(set(df["name"].tolist()))
        }), 404

    # Parse optional params
    try:
        top_k = int(request.args.get("top_k", 5))
    except ValueError:
        top_k = 5
    cheaper_than = request.args.get("cheaper_than", "true").lower() in ("1", "true", "yes")
    price_cap = request.args.get("price_cap")
    price_cap = float(price_cap) if price_cap is not None else None

    results = recommend(idx, top_k=top_k, price_cap=price_cap, cheaper_than=cheaper_than)
    base = df.loc[idx]
    return jsonify({
        "query": {
            "name": base["name"],
            "brand": base["brand"],
            "price": float(base["price"])
        },
        "params": {
            "top_k": top_k,
            "cheaper_than": cheaper_than,
            "price_cap": price_cap
        },
        "results": results
    })

if __name__ == "__main__":
    # debug=True enables hot reload; fine for local dev
    app.run(host="127.0.0.1", port=5000, debug=True)
