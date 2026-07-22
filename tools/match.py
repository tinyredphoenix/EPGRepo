import json, csv, pathlib
HERE = pathlib.Path(__file__).resolve().parent
from match_lib import best_match_in_corpus

with open(HERE / "data" / "corpus.json", encoding="utf-8") as f:
    corpus = json.load(f)

def load_list(path, provider):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append((provider, line))
    return out

items = load_list(HERE / "raw_lists" / "meowfy_raw.txt", "meowfy") + \
        load_list(HERE / "raw_lists" / "sktech_relevant.txt", "sktech")

rows = []
for provider, raw in items:
    matches = best_match_in_corpus(raw, corpus)
    if matches:
        top_xid, top_score, top_txt = matches[0]
        rows.append({
            "provider": provider, "raw_name": raw, "xmltv_id": top_xid,
            "score": round(top_score, 1), "matched_via": top_txt,
            "db_name": corpus[top_xid]["db_name"], "grab_site": corpus[top_xid]["grab_site"],
            "alt2_id": matches[1][0] if len(matches) > 1 else "",
            "alt2_score": round(matches[1][1], 1) if len(matches) > 1 else "",
            "alt3_id": matches[2][0] if len(matches) > 2 else "",
            "alt3_score": round(matches[2][1], 1) if len(matches) > 2 else "",
        })
    else:
        rows.append({
            "provider": provider, "raw_name": raw, "xmltv_id": "", "score": 0,
            "matched_via": "", "db_name": "", "grab_site": "",
            "alt2_id": "", "alt2_score": "", "alt3_id": "", "alt3_score": "",
        })

with open(HERE / "data" / "match_results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

auto = [r for r in rows if r["score"] >= 90]
review = [r for r in rows if 75 <= r["score"] < 90]
unmatched = [r for r in rows if r["score"] < 75]
print(f"total: {len(rows)}  auto(>=90): {len(auto)}  review(75-89): {len(review)}  unmatched(<75): {len(unmatched)}")
print(f"unique xmltv_ids matched (auto+review): {len(set(r['xmltv_id'] for r in auto+review if r['xmltv_id']))}")
