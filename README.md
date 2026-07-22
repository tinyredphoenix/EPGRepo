# Unified EPG for Meowfy + SK Tech

Generates a single XMLTV guide covering channels from both providers, so you
don't have to point TiviMate at two different EPG sources or manually flip
between them. A GitHub Action refreshes the programme data automatically.

## How it works

```
data/mapping.csv  --(build_channels_xml.py)-->  channels.xml + aliases.json
                                                        |
                                        npm run grab (iptv-org/epg)
                                                        |
                                                   guide.xml
                                                        |
                                    (postprocess.py: add name aliases, gzip)
                                                        |
                                    output/epg.xml + output/epg.xml.gz
```

- **`data/mapping.csv`** is the source of truth for channel identity — one
  row per raw channel name (from either provider), mapped to a real,
  currently-grabbable channel ID and a single guide source. This file is
  fully static between runs: the Action never re-guesses channel identity,
  it only re-fetches programme data for exactly the channels you've
  approved. That's what makes it "single source, no switching."
- **One grab source per channel.** Where a channel is matched, I picked one
  source (priority: dishtv.in → airtelxstream.in → zee5.com → tataplay.com →
  jiotv.com) and stuck with it — never alternates at runtime.
- **Both providers' spellings become aliases.** Since neither provider's
  actual `tvg-id` was available to build this against, every channel in the
  final `epg.xml` carries *every* known display name (Meowfy's, SK Tech's,
  and the guide source's own) as extra `<display-name>` tags, to maximize
  TiviMate's name-based auto-matching.

## Current coverage

Out of ~1,235 relevant raw channel names across both providers:
- **657 channels** matched with high confidence and are grabbed automatically.
- **~47 more** matched but are flagged `review` in `mapping.csv` — check
  these once, then flip `include` to `yes` if they look right.
- **~153 names** had no confident match at all and are listed in
  `data/needs_manual_mapping.csv` for you to map by hand if you know the
  channel (add a row to `mapping.csv` with the right `xmltv_id`/site/site_id).

## A note on match accuracy — please skim `mapping.csv` before relying on it

Fuzzy text matching has a specific failure mode: **"Star Sports 1" and "Star
Sports 2" differ by one character, so naive matching scores them as ~95%
similar even though they're completely different channels.** The matcher
here has an explicit guard against this (see `tools/README.md` for details —
it blocks/penalizes any match where the channel numbers disagree, and
prefers a channel's current name over old pre-rebrand alt-names), and I
audited the whole numbered-channel family (Star Gold/Gold 2, Star Sports
1/2/3 × Hindi/Tamil/Telugu/Kannada, Sony Max 1/2, Ten 1/2/3, SVBC 2/3/4,
Colors Kannada/Kannada Cinema, Zee Cinema/Cinemalu, etc.) after adding it —
all resolved to distinct, correct IDs.

That said: this is still automated matching over ~1,200 names, not a manual
channel-by-channel verification. Treat `mapping.csv` as a strong first draft:
- Rows with `confidence=auto` (score ≥ 90) are very likely correct.
- Rows with `confidence=likely`/`review` are worth a 5-second glance,
  especially for channels where you'd actually notice a wrong guide (movies,
  sports feeds you watch a lot).
- If you ever see wrong programme data for a channel in TiviMate, open
  `mapping.csv`, find that channel's `xmltv_id`, and either fix the
  `grab_site`/`grab_site_id`/`xmltv_id` by hand or set `include=no`.

## Setup

1. Push this repo to GitHub.
2. In **Settings → Actions → General → Workflow permissions**, select
   "Read and write permissions" (needed so the Action can commit the
   updated guide back to the repo).
3. Run the workflow once manually: **Actions → Update EPG → Run workflow**.
4. After it finishes, your EPG URL is:
   ```
   https://raw.githubusercontent.com/<you>/<repo>/main/output/epg.xml.gz
   ```
   (or `output/epg.xml` uncompressed).

## Using it in TiviMate

Settings → Playlists → (your playlist) → EPG → Add EPG source → paste the
URL above (the `.xml.gz` one is smaller/faster). Since programme matching
falls back to channel name (not just `tvg-id`), TiviMate should auto-link
most channels; for stragglers, use TiviMate's manual "Assign channel" EPG
matching UI — the alias names baked into the guide should make your exact
channel easy to find in that picker even if it doesn't auto-link.

## Editing the channel mapping

Open `data/mapping.csv` in a spreadsheet editor. Columns:

| column | meaning |
|---|---|
| `include` | `yes` = grabbed by the Action, `review` = matched but not grabbed yet, `no` = ignore |
| `xmltv_id` | the canonical channel ID used in the output guide |
| `raw_name` | the exact name as it appeared in your provider's channel list |
| `provider` | `meowfy` or `sktech` |
| `confidence` / `score` | how sure the matcher was |
| `grab_site` / `grab_site_id` | where programme data is fetched from |

Commit changes to `main` — the Action is also triggered on pushes that touch
`data/mapping.csv`, so it'll refresh within a minute or two.

## Schedule

Runs twice daily (03:15 and 15:15 UTC) plus on-demand via the Actions tab.
Edit the `cron` line in `.github/workflows/update-epg.yml` to change this.
