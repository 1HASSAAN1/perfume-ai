# Perfume AI – Dupe Finder & Recommendation API

An AI-powered tool that suggests **cheaper dupes** and similar fragrances based on scent profiles.  
Built with Python, scikit-learn, and Flask — perfect for perfume lovers and collectors.

## ✨ Features
- **Dupe Finder** – find cheaper alternatives to expensive perfumes
- **Similarity Scoring** – based on scent accords and notes
- **Flask API** – easy to integrate with websites or mobile apps
- **Custom Filters** – limit by price, change result count, toggle cheaper-only mode
- **Extensible Dataset** – start small, expand to thousands of perfumes

## 🚀 Live Demo (Local)
```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/perfume-ai.git
cd perfume-ai

# 2. Create virtual environment
python -m venv venv
# (Windows) Activate:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; .\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run API
python src/api.py
