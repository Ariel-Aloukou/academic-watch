from flask import Flask, jsonify, send_from_directory
import json
from pathlib import Path

app = Flask(__name__)
DATA_DIR = Path("data")

@app.route("/api/opportunities")
def opportunities():
    """Retourne toutes les opportunités stockées dans data/"""
    results = []
    if DATA_DIR.exists():
        for fiche in DATA_DIR.glob("*.json"):
            try:
                data = json.loads(fiche.read_text(encoding="utf-8"))
                results.append(data)
            except Exception:
                continue
    return jsonify(results)

@app.route("/")
def index():
    return "Academic Watch API - Utilisez /api/opportunities"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)