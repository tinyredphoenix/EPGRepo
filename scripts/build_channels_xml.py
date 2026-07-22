#!/usr/bin/env python3
"""
Reads data/mapping.csv (the human-reviewed channel mapping) and produces:
  - channels.xml   : the custom channel list fed to `npm run grab -- --channels=`
  - aliases.json    : xmltv_id -> [all known display names across both
                       providers], used by postprocess.py to add extra
                       <display-name> tags so TiviMate's name-based matching
                       has the best possible shot even without tvg-id access.

Only rows with include=yes are grabbed. This keeps channel identity 100%
deterministic between runs: the Action never re-runs the fuzzy matcher, it
only re-fetches programme data for the exact channel set you've approved in
mapping.csv. To add/fix a channel, edit mapping.csv and commit -- that's the
only place channel identity is decided.
"""
import csv
import json
import sys
import xml.sax.saxutils as sax
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPPING_CSV = ROOT / "data" / "mapping.csv"
CHANNELS_XML = ROOT / "channels.xml"
ALIASES_JSON = ROOT / "aliases.json"


def main():
    with open(MAPPING_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    included = [r for r in rows if r["include"].strip().lower() == "yes"]
    if not included:
        print("ERROR: no rows with include=yes in mapping.csv -- nothing to grab.", file=sys.stderr)
        sys.exit(1)

    by_id = defaultdict(list)
    for r in included:
        by_id[r["xmltv_id"]].append(r)

    channel_lines = []
    aliases = {}
    site_counts = defaultdict(int)

    for xmltv_id, group in sorted(by_id.items()):
        rep = group[0]  # grab_site/grab_site_id are identical across the group by construction
        site = rep["grab_site"]
        site_id = rep["grab_site_id"]
        display = rep["matched_db_name"] or rep["raw_name"]
        site_counts[site] += 1

        channel_lines.append(
            f'  <channel site="{sax.escape(site)}" site_id="{sax.escape(site_id)}" '
            f'xmltv_id="{sax.escape(xmltv_id)}" lang="en">{sax.escape(display)}</channel>'
        )

        names = []
        seen = set()
        for r in group:
            n = r["raw_name"].strip()
            key = n.lower()
            if n and key not in seen:
                seen.add(key)
                names.append(n)
        if display.lower() not in seen:
            names.insert(0, display)
        aliases[xmltv_id] = names

    xml_out = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<channels>\n'
        + "\n".join(channel_lines)
        + "\n</channels>\n"
    )
    CHANNELS_XML.write_text(xml_out, encoding="utf-8")
    ALIASES_JSON.write_text(json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {CHANNELS_XML} with {len(by_id)} channels:")
    for site, n in sorted(site_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {site}: {n}")
    print(f"Wrote {ALIASES_JSON} ({sum(len(v) for v in aliases.values())} total alias names)")


if __name__ == "__main__":
    main()
