#!/usr/bin/env python3
"""
Takes the raw guide.xml produced by `npm run grab` and:
  1. Adds every known alias name (from aliases.json, i.e. both Meowfy's and
     SK Tech's original spelling) as an extra <display-name> on each
     <channel>, so TiviMate's name-based auto-matching has the best chance
     of linking up even without tvg-id access.
  2. Writes the final output/epg.xml and a gzipped output/epg.xml.gz.
"""
import gzip
import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
ALIASES_JSON = ROOT / "aliases.json"
GUIDE_XML = ROOT / "guide.xml"
OUT_DIR = ROOT / "output"
OUT_XML = OUT_DIR / "epg.xml"
OUT_GZ = OUT_DIR / "epg.xml.gz"


def main():
    if not GUIDE_XML.exists():
        print(f"ERROR: {GUIDE_XML} not found -- did the grab step run/succeed?", file=sys.stderr)
        sys.exit(1)

    aliases = json.loads(ALIASES_JSON.read_text(encoding="utf-8")) if ALIASES_JSON.exists() else {}

    tree = ET.parse(GUIDE_XML)
    root = tree.getroot()

    n_channels = 0
    n_programmes = 0
    for el in root:
        if el.tag == "channel":
            n_channels += 1
            cid = el.get("id", "")
            existing = {dn.text.strip().lower() for dn in el.findall("display-name") if dn.text}
            icon_el = el.find("icon")
            for name in aliases.get(cid, []):
                if name.strip().lower() not in existing:
                    dn = ET.Element("display-name")
                    dn.text = name
                    if icon_el is not None:
                        icon_el.addprevious(dn) if hasattr(icon_el, "addprevious") else el.insert(
                            list(el).index(icon_el), dn
                        )
                    else:
                        el.append(dn)
                    existing.add(name.strip().lower())
        elif el.tag == "programme":
            n_programmes += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tree.write(OUT_XML, encoding="UTF-8", xml_declaration=True)

    with open(OUT_XML, "rb") as f_in, gzip.open(OUT_GZ, "wb") as f_out:
        f_out.writelines(f_in)

    print(f"Wrote {OUT_XML} and {OUT_GZ}: {n_channels} channels, {n_programmes} programmes")


if __name__ == "__main__":
    main()
