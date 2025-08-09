# prepare_dataset.py  — tailored for semicolon CSV like your fra_cleaned.csv

from pathlib import Path
import pandas as pd
import re

RAW_FILE = Path("raw_data/fra_cleaned.csv")    # your file
OUT_FILE = Path("data/perfumes_clean.csv")

# ---------- Robust CSV loader (semicolon + encoding fallback) ----------
def load_csv_flexible(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, sep=";", encoding="utf-8", on_bad_lines="skip")
    except UnicodeDecodeError:
        print(f"⚠️ {path.name} not UTF-8 — trying latin1 …")
        return pd.read_csv(path, sep=";", encoding="latin1", on_bad_lines="skip")

# ---------- Helpers ----------
def normalize_list_field(val: str) -> str:
    """Turn 'citrus, woody; aromatic' into 'citrus; woody; aromatic' (lowercased, deduped)."""
    if pd.isna(val):
        return ""
    s = str(val).lower().replace(";", ",")
    parts = [p.strip() for p in s.split(",") if p.strip()]
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return "; ".join(out)

def parse_rating(x):
    if pd.isna(x):
        return None
    s = str(x).strip().replace(",", ".")  # e.g. "1,93" -> "1.93"
    try:
        return float(s)
    except:
        return None

# ---------- Main ----------
def main():
    if not RAW_FILE.exists():
        print(f"❌ {RAW_FILE} not found. Put your CSV there.")
        return

    df = load_csv_flexible(RAW_FILE)
    print(f"Loaded {len(df):,} raw rows from {RAW_FILE.name}")

    # Map your exact headers (case-sensitive as in your sample)
    name_col   = "Perfume" if "Perfume" in df.columns else None
    brand_col  = "Brand"   if "Brand"   in df.columns else None
    year_col   = "Year"    if "Year"    in df.columns else None
    gender_col = "Gender"  if "Gender"  in df.columns else None

    # mainaccord1..5 -> accords
    accord_cols = [c for c in df.columns if str(c).lower().startswith("mainaccord")]

    # Top/Middle/Base -> merged notes
    top_col    = "Top"    if "Top"    in df.columns else None
    middle_col = "Middle" if "Middle" in df.columns else None
    base_col   = "Base"   if "Base"   in df.columns else None

    rating_col = "Rating Value" if "Rating Value" in df.columns else None
    votes_col  = "Rating Count" if "Rating Count" in df.columns else None

    # Build accords (combine mainaccord1..5)
    if accord_cols:
        accords = (
            df[accord_cols]
            .astype(str)
            .apply(lambda row: "; ".join([x for x in row if str(x).strip() not in ("", "nan")]), axis=1)
            .apply(normalize_list_field)
        )
    else:
        accords = pd.Series([""] * len(df))

    # Build notes (combine Top/Middle/Base)
    def combine_notes(row):
        buckets = []
        for c in (top_col, middle_col, base_col):
            if c and pd.notna(row.get(c)):
                buckets.append(str(row[c]))
        return normalize_list_field("; ".join(buckets)) if buckets else ""
    notes = df.apply(combine_notes, axis=1)

    # Optional rating/votes
    rating = df[rating_col].apply(parse_rating) if rating_col else None
    votes  = df[votes_col] if votes_col else None

    # Assemble output for API
    clean = pd.DataFrame({
        "name":   df[name_col].astype(str).str.strip() if name_col  else "",
        "brand":  df[brand_col].astype(str).str.strip() if brand_col else "",
        "year":   df[year_col]   if year_col   else "",
        "gender": df[gender_col] if gender_col else "",
        "accords": accords,
        "notes":   notes,
        "price_gbp": None,   # this dataset doesn’t have prices
        "longevity": "",
        "sillage":   "",
        "rating":    rating,
        "votes":     votes,
    })

    # Drop empties + dedupe (brand+name), then build profile_text
    before = len(clean)
    clean = clean[(clean["name"] != "") & (clean["brand"] != "")].copy()
    key = (clean["brand"].str.lower().str.strip() + " :: " + clean["name"].str.lower().str.strip())
    clean = clean.loc[~key.duplicated()].copy()

    clean["profile_text"] = (
        clean["accords"].fillna("") + " " + clean["notes"].fillna("")
    ).str.lower().str.replace(";", " ", regex=False)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(OUT_FILE, index=False)
    print(f"✅ Wrote {OUT_FILE} with {len(clean):,} rows (from {before:,} after filtering).")

if __name__ == "__main__":
    main()
