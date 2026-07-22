import csv, json, pathlib
HERE = pathlib.Path(__file__).resolve().parent

with open(HERE / "data" / "corpus.json", encoding="utf-8") as f:
    corpus = json.load(f)

with open(HERE / "data" / "match_results.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

mapping_rows = []
unmatched_rows = []

for r in rows:
    score = float(r["score"])
    if not r["xmltv_id"] or score < 75:
        unmatched_rows.append({
            "raw_name": r["raw_name"],
            "provider": r["provider"],
            "best_guess_xmltv_id": r["xmltv_id"],
            "best_guess_score": r["score"],
        })
        continue
    confidence = "auto" if score >= 90 else ("likely" if score >= 85 else "review")
    include = "yes" if score >= 85 else "review"
    entry = corpus[r["xmltv_id"]]
    mapping_rows.append({
        "include": include,
        "xmltv_id": r["xmltv_id"],
        "raw_name": r["raw_name"],
        "provider": r["provider"],
        "confidence": confidence,
        "score": round(score, 1),
        "matched_db_name": r["db_name"],
        "grab_site": entry["grab_site"],
        "grab_site_id": entry["grab_site_id"],
    })

mapping_rows.sort(key=lambda x: (x["xmltv_id"], x["provider"]))
unmatched_rows.sort(key=lambda x: (x["provider"], x["raw_name"]))

with open(HERE.parent / "data" / "mapping.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(mapping_rows[0].keys()))
    w.writeheader()
    w.writerows(mapping_rows)

with open(HERE.parent / "data" / "needs_manual_mapping.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(unmatched_rows[0].keys()))
    w.writeheader()
    w.writerows(unmatched_rows)

n_channels = len(set(r["xmltv_id"] for r in mapping_rows))
n_yes = len(set(r["xmltv_id"] for r in mapping_rows if r["include"] == "yes"))
print(f"mapping.csv: {len(mapping_rows)} rows / {n_channels} unique channels ({n_yes} auto-included, "
      f"{n_channels - n_yes} flagged 'review')")
print(f"needs_manual_mapping.csv: {len(unmatched_rows)} raw names with no confident match")
