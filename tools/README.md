# Maintenance tools (optional, not run by the Action)

These are the scripts used to build `data/mapping.csv` in the first place.
The daily Action does **not** use these — it only reads the committed
`mapping.csv`. Re-run this pipeline only when your provider channel lists
change substantially and you want fresh candidate matches.

## How the matching works (and why it's safe)

1. `build_index.py` builds a corpus of ~770 real, currently-grabbable Indian
   channels from `iptv-org/database` (the canonical channel directory) plus
   the channel lists already mapped by four DTH/OTT guide sources
   (dishtv.in, airtelxstream.in, zee5.com, tataplay.com) in `iptv-org/epg`.
2. `match.py` fuzzy-matches your raw channel names against that corpus.
3. `match_jiotv.py` does a second pass against JioTV's larger (1094-channel)
   but unofficial list, for names step 2 couldn't place.
4. `finalize_mapping.py` writes `data/mapping.csv` for you to review.

**Important guard:** plain fuzzy/edit-distance matching will happily score
"Star Sports 1" vs "Star Sports 2" as a 90%+ match, because only one
character differs — that's how genuinely different channels get merged.
`match_lib.py` adds a hard rule: if the query and the candidate's *current
canonical name* both contain numbers and those numbers differ (Star Sports
**1** vs **2**, Sony Max **1** vs **2**, Ten **1**/**2**/**3**, SVBC **2**/**3**,
etc.), the match is either heavily penalized or blocked outright, regardless
of how similar the surrounding text is. It also trusts a channel's *current*
name more than its `alt_names` (which can be old, pre-rebrand names — this is
literally why "Star Sports 3" was initially mismatching to "Star Sports 1
Hindi": that channel was *previously* branded "Star Sports 3" before a
rebrand, and it's recorded as an alt_name in the database).

Even with this guard, **fuzzy matching can still be wrong** — that's why
every match lands in `mapping.csv` with a `confidence` (auto/likely/review)
and `score`, and only `include=yes` rows are ever grabbed. Spot-check
anything below 90, especially numbered/regional variants you care about.

## Re-running

```sh
git clone --depth 1 https://github.com/iptv-org/database.git tools/database
git clone --depth 1 https://github.com/iptv-org/epg.git tools/epg
cd tools
pip install rapidfuzz
python3 build_index.py
python3 match.py
python3 finalize_mapping.py
python3 match_jiotv.py
# review data/mapping.csv and data/needs_manual_mapping.csv, then copy
# mapping.csv over the one in the repo root's data/ folder.
```

To add new raw channel names, drop them (one per line) into
`raw_lists/meowfy_raw.txt` or `raw_lists/sktech_relevant.txt` before running
`match.py`.
