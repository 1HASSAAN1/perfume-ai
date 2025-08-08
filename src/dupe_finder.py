import sys
from pathlib import Path
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import get_close_matches

# Always resolve to <project_root>/data/perfumes_sample.csv
DATA_PATH = (Path(__file__).resolve().parent.parent / "data" / "perfumes_sample.csv")

def load_data(path=DATA_PATH):
    # sanity check (helps debug paths)
    # print("Reading:", path)  # uncomment if needed
    df = pd.read_csv(path)
    df["profile_text"] = (df["accords"].fillna("") + " " + df["notes"].fillna("")).str.lower()
    return df


def build_model(corpus):
    vec = TfidfVectorizer(token_pattern=r"[A-Za-zÀ-ÿ']+")
    X = vec.fit_transform(corpus)
    return vec, X

def find_index_by_name(df, query):
    # Exact first
    matches = df.index[df["name"].str.lower() == query.lower()].tolist()
    if matches:
        return matches[0]
    # Fuzzy fallback
    options = df["name"].tolist()
    guess = get_close_matches(query, options, n=1, cutoff=0.6)
    if guess:
        return df.index[df["name"] == guess[0]][0]
    return None

def recommend(df, X, idx, top_k=5, price_cap=None, cheaper_than=True):
    sims = cosine_similarity(X[idx], X).flatten()
    # make a frame with scores
    out = df.copy()
    out["similarity"] = sims
    # filter out the same item
    out = out[out.index != idx]
    # optional price filters
    if price_cap is not None:
        out = out[out["price"] <= price_cap]
    if cheaper_than:
        out = out[out["price"] < df.loc[idx, "price"]]
    # sort and take top
    out = out.sort_values("similarity", ascending=False).head(top_k)
    return out[["name", "brand", "price", "similarity"]]

def main():
    if len(sys.argv) >= 2:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Enter a perfume you like: ").strip()

    df = load_data()
    vec, X = build_model(df["profile_text"])
    idx = find_index_by_name(df, query)
    if idx is None:
        print(f"Couldn't find '{query}' in the dataset.")
        print("Try one of:", ", ".join(sorted(set(df['name']))))
        sys.exit(1)

    base = df.loc[idx]
    print(f"\nYou chose: {base['name']} ({base['brand']})  | Price: £{base['price']}")
    print("Finding similar, cheaper dupes...\n")

    recs = recommend(df, X, idx, top_k=5, price_cap=None, cheaper_than=True)
    if recs.empty:
        print("No cheaper close matches found. Showing closest overall:")
        recs = recommend(df, X, idx, top_k=5, price_cap=None, cheaper_than=False)

    # pretty print
    for i, row in recs.reset_index(drop=True).iterrows():
        sim = f"{row['similarity']*100:.1f}%"
        print(f"{i+1}. {row['name']} — {row['brand']}  | £{row['price']}  | Similarity: {sim}")

if __name__ == "__main__":
    main()
