"""
Build a matching corpus from iptv-org/database + the pre-mapped site channel
files that already carry a real xmltv_id (dishtv.in, airtelxstream.in,
zee5.com, tataplay.com). Output: data/corpus.json
  { xmltv_id: { "names": [...all known display variants...],
                "sources": {site: site_id, ...},
                "db_name": "...", "country": "IN" } }
"""
import csv, json, os, pathlib
from collections import defaultdict
import xml.etree.ElementTree as ET

DB = str(pathlib.Path(__file__).resolve().parent / "database" / "data")
SITES_DIR = str(pathlib.Path(__file__).resolve().parent / "epg" / "sites")
SOURCE_FILES = {
    "dishtv.in": "dishtv.in/dishtv.in.channels.xml",
    "airtelxstream.in": "airtelxstream.in/airtelxstream.in.channels.xml",
    "zee5.com": "zee5.com/zee5.com.channels.xml",
    "tataplay.com": "tataplay.com/tataplay.com.channels.xml",
}
# priority order = first one that has the channel wins as the grab source
SITE_PRIORITY = ["dishtv.in", "airtelxstream.in", "zee5.com", "tataplay.com"]

channels = {}
with open(f"{DB}/channels.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        channels[row["id"]] = row

def base_id(xmltv_id):
    return xmltv_id.split("@")[0]

def is_mostly_ascii(name: str) -> bool:
    ascii_chars = sum(1 for c in name if ord(c) < 128)
    return len(name) > 0 and ascii_chars / len(name) >= 0.85

corpus = defaultdict(lambda: {"names": {}, "sources": {}, "db_name": "", "country": "", "categories": ""})

for site, relpath in SOURCE_FILES.items():
    path = os.path.join(SITES_DIR, relpath)
    tree = ET.parse(path)
    root = tree.getroot()
    for ch in root.findall("channel"):
        xid = ch.get("xmltv_id")
        site_id = ch.get("site_id")
        text = (ch.text or "").strip()
        if not xid or not text:
            continue
        entry = corpus[xid]
        if is_mostly_ascii(text):
            # a live guide source calling it this name is strong evidence
            entry["names"][text] = "site"
        if site not in entry["sources"]:
            entry["sources"][site] = site_id

for xid, entry in corpus.items():
    bid = base_id(xid)
    row = channels.get(bid)
    if row:
        entry["db_name"] = row["name"]
        entry["country"] = row["country"]
        entry["categories"] = row["categories"]
        if is_mostly_ascii(row["name"]):
            entry["names"][row["name"]] = "primary"   # current canonical name: highest trust
        for alt in (row.get("alt_names") or "").split(";"):
            alt = alt.strip()
            if alt and is_mostly_ascii(alt) and alt not in entry["names"]:
                entry["names"][alt] = "alt"            # may be a historical/rebrand name: lower trust

out = {}
for xid, entry in corpus.items():
    grab_site = None
    for s in SITE_PRIORITY:
        if s in entry["sources"]:
            grab_site = s
            break
    out[xid] = {
        "names": entry["names"],   # {name: "primary"|"site"|"alt"}
        "grab_site": grab_site,
        "grab_site_id": entry["sources"].get(grab_site),
        "all_sources": entry["sources"],
        "db_name": entry["db_name"],
        "country": entry["country"],
        "categories": entry["categories"],
    }

OUT = pathlib.Path(__file__).resolve().parent / "data"
OUT.mkdir(exist_ok=True)
with open(OUT / "corpus.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"Built corpus with {len(out)} canonical channels")
