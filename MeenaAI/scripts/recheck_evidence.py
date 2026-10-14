
import json
import re
import unicodedata
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CANDIDATES = DATA / "quality_needs_review.jsonl"
PASSAGES = DATA / "eligible_passages.jsonl"
OUTPUT = DATA / "evidence_recheck_report.json"

def read_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def normalize(text):
    text = unicodedata.normalize("NFKC", str(text or "")).lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()

candidates = read_jsonl(CANDIDATES)
passages = read_jsonl(PASSAGES)

def passage_text(p):
    for key in ("text", "passage", "content", "page_text"):
        if p.get(key):
            return str(p[key])
    return ""

def same_source(candidate, passage):
    if candidate.get("source_id") != passage.get("source_id"):
        return False

    # Match by passage ID if both records provide one.
    cp = candidate.get("passage_id")
    pp = passage.get("passage_id")
    if cp and pp:
        return cp == pp

    # Otherwise use overlapping page ranges when available.
    cs = candidate.get("page_start")
    ce = candidate.get("page_end", cs)
    ps = passage.get("page_start")
    pe = passage.get("page_end", ps)

    if cs is not None and ps is not None:
        try:
            return int(cs) <= int(pe) and int(ps) <= int(ce)
        except (TypeError, ValueError):
            return False

    return False

reviewed = [
    r for r in candidates
    if "evidence_quote_not_found" in r.get("review_reasons", [])
    or "evidence_quote_not_found" in r.get("review_flags", [])
]

results = []
counts = Counter()

for row in reviewed:
    quote = normalize(row.get("evidence_quote", ""))
    matching_passages = [p for p in passages if same_source(row, p)]

    found = bool(
        quote and len(quote) >= 15 and any(
            quote in normalize(passage_text(p))
            for p in matching_passages
        )
    )

    results.append({
        "source_id": row.get("source_id"),
        "question": row.get("question"),
        "answer": row.get("answer"),
        "evidence_quote": row.get("evidence_quote"),
        "normalized_quote_found": found,
        "matching_passages": len(matching_passages),
        "review_required": True
    })

    counts["normalized_match_found" if found else "still_unmatched"] += 1

report = {
    "records_rechecked": len(results),
    "results": dict(counts),
    "note": (
        "A normalized quote match only confirms text traceability. "
        "It does not establish answer correctness or license approval."
    ),
    "records": results
}

if OUTPUT.exists():
    raise SystemExit(
        f"Output already exists: {OUTPUT}\n"
        "Rename or move it before rerunning."
    )

OUTPUT.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("Evidence recheck complete.")
print("Records rechecked:", len(results))
print("Normalized matches:", counts["normalized_match_found"])
print("Still unmatched:", counts["still_unmatched"])
print("Report:", OUTPUT)
