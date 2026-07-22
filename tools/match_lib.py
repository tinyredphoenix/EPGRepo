import re
from rapidfuzz import fuzz

NOISE_TOKENS = {
    "hd", "fhd", "uhd", "sd", "hq", "4k", "hevc", "h265", "h264",
    "east", "west", "bk", "na", "eu", "usa", "uk", "live", "international",
}

PROVENANCE_WEIGHT = {"primary": 1.0, "site": 1.0, "alt": 0.80}


def normalize(name: str) -> str:
    n = name.lower()
    n = re.sub(r"\[[^\]]*\]", " ", n)      # strip [IN] [BENGALI] etc.
    n = re.sub(r"\([^)]*\)", " ", n)       # strip (BK) (NA) etc.
    n = n.replace("&", " and ")
    n = re.sub(r"[^a-z0-9]+", " ", n)      # punctuation -> space
    tokens = [t for t in n.split() if t not in NOISE_TOKENS]
    return " ".join(tokens).strip()


def digit_tokens(s: str) -> set:
    """All standalone numbers, e.g. 'Star Sports 1 Hindi' -> {'1'}."""
    return set(re.findall(r"\d+", s))


def digit_guard_penalty(query_norm: str, primary_name_norm: str) -> float:
    """
    Channel numbering (Star Sports 1 vs 2, Sony Max 1 vs 2, Ten 1 vs 2 ...) is a
    hard discriminator, not a fuzzy one -- plain edit-distance scoring treats
    '1'->'2' as a 1-character difference and will happily score it 90%+, which
    is exactly how wrong channels get merged. This must dominate the final
    score, not just nudge it.
    """
    qd = digit_tokens(query_norm)
    pd = digit_tokens(primary_name_norm)
    if qd and pd and qd != pd:
        return 65.0   # different numbered feed: near-disqualifying
    if bool(qd) != bool(pd):
        return 22.0   # one side numbered, other isn't: genuinely ambiguous, force review
    return 0.0


def combined_score(q: str, cand: str) -> float:
    r = fuzz.ratio(q, cand)
    ts = fuzz.token_sort_ratio(q, cand)
    score = 0.6 * r + 0.4 * ts
    lq, lc = len(q.split()), len(cand.split())
    if lc != lq:
        score -= 6 * abs(lc - lq)
    return max(score, 0)


def best_match_in_corpus(raw_name: str, corpus: dict, limit=3, score_cutoff=55):
    """
    corpus: { xmltv_id: {"names": {name: provenance}, "db_name": ..., ...} }
    Returns [(xmltv_id, score, matched_text), ...] sorted best first.
    """
    q = normalize(raw_name)
    if not q:
        return []
    best = {}  # xmltv_id -> (score, matched_text)
    for xid, entry in corpus.items():
        primary_norm = normalize(entry.get("db_name") or "")
        penalty = digit_guard_penalty(q, primary_norm) if primary_norm else 0.0
        local_best = None
        for name, provenance in entry["names"].items():
            cand = normalize(name)
            if not cand:
                continue
            raw_score = combined_score(q, cand) * PROVENANCE_WEIGHT.get(provenance, 0.8)
            if local_best is None or raw_score > local_best[0]:
                local_best = (raw_score, name)
        if local_best is None:
            continue
        final_score = max(local_best[0] - penalty, 0)
        if final_score < score_cutoff:
            continue
        if xid not in best or final_score > best[xid][0]:
            best[xid] = (final_score, local_best[1])
    ranked = sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)[:limit]
    return [(xid, score, txt) for xid, (score, txt) in ranked]
