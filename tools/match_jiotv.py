import csv, pathlib
import xml.etree.ElementTree as ET
HERE = pathlib.Path(__file__).resolve().parent
from match_lib import best_match_in_corpus, normalize

def slugify(name: str) -> str:
    return __import__("re").sub(r"[^A-Za-z0-9]", "", name)

# Build a pseudo-corpus from jiotv's channel list: one entry per site_id,
# with a single "primary" name -- so the same digit guard used for the main
# corpus (Star Sports 1 vs 2, etc.) applies here too.
tree = ET.parse(HERE / "epg" / "sites" / "jiotv.com" / "jiotv.com.channels.xml")
jio_corpus = {}
for ch in tree.getroot().findall("channel"):
    site_id = ch.get("site_id")
    text = (ch.text or "").strip()
    if not text:
        continue
    xid = f"{slugify(text)}.in@jiotv"
    # if two different jio channels slugify to the same id, keep them distinct
    # by site_id suffix so they don't collide
    if xid in jio_corpus and jio_corpus[xid]["_site_id"] != site_id:
        xid = f"{slugify(text)}-{site_id}.in@jiotv"
    jio_corpus[xid] = {"names": {text: "primary"}, "db_name": text, "_site_id": site_id}

with open(HERE.parent / "data" / "needs_manual_mapping.csv", encoding="utf-8") as f:
    unmatched = list(csv.DictReader(f))

still_unmatched = []
jio_matches = []

for row in unmatched:
    raw = row["raw_name"]
    matches = best_match_in_corpus(raw, jio_corpus, limit=1, score_cutoff=80)
    if matches:
        xid, score, matched_text = matches[0]
        entry = jio_corpus[xid]
        confidence = "auto" if score >= 92 else "likely"
        jio_matches.append({
            "include": "yes" if score >= 85 else "review",
            "xmltv_id": xid,
            "raw_name": raw,
            "provider": row["provider"],
            "confidence": confidence,
            "score": round(score, 1),
            "matched_db_name": entry["db_name"],
            "grab_site": "jiotv.com",
            "grab_site_id": entry["_site_id"],
        })
    else:
        still_unmatched.append(row)

print(f"jiotv second pass: {len(jio_matches)} more raw names matched "
      f"({len(set(m['xmltv_id'] for m in jio_matches))} unique jiotv channels), "
      f"{len(still_unmatched)} still unmatched")

with open(HERE.parent / "data" / "mapping.csv", encoding="utf-8") as f:
    existing = list(csv.DictReader(f))
fieldnames = list(existing[0].keys())
all_rows = existing + jio_matches
all_rows.sort(key=lambda x: (x["xmltv_id"], x["provider"]))
with open(HERE.parent / "data" / "mapping.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(all_rows)

with open(HERE.parent / "data" / "needs_manual_mapping.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(unmatched[0].keys()))
    w.writeheader()
    w.writerows(still_unmatched)

n_channels_total = len(set(r["xmltv_id"] for r in all_rows))
print(f"mapping.csv now: {len(all_rows)} rows / {n_channels_total} unique channels total")
