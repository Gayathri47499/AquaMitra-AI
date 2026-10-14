
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

REVIEW_FILE = DATA / "quality_needs_review.jsonl"
PASSAGE_FILE = DATA / "eligible_passages.jsonl"
OUTPUT_FILE = DATA / "evidence_recovery_report.json"

def read_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def norm(value):
    return " ".join(str(value or "").lower().split())

reviews = read_jsonl(REVIEW_FILE)
passages = read_jsonl(PASSAGE_FILE)

passage_by_id = {
    p.get("passage_id"): p
    for p in passages if p.get("passage_id")
}

results = []
matched = 0
unmatched = 0

for row in reviews:
    flags = row.get("quality_flags", [])
    if "evidence_quote_not_found" not in flags:
        continue

    passage = passage_by_id.get(row.get("passage_id"))
    quote = norm(row.get("evidence_quote"))
    source_text = ""

    if passage:
        for key in ("text", "passage", "content", "page_text"):
            if passage.get(key):
                source_text = norm(passage[key])
                break

    found = bool(quote and source_text and quote in source_text)

    results.append({
        "source_id": row.get("source_id"),
        "passage_id": row.get("passage_id"),
        "question": row.get("question"),
        "answer": row.get("answer"),
        "evidence_quote": row.get("evidence_quote"),
        "passage_found": passage is not None,
        "quote_found_after_whitespace_normalization": found,
        "status": "SOURCE_MATCH_REQUIRES_REVIEW" if found
                  else "UNMATCHED_REQUIRES_REVIEW"
    })

    if found:
        matched += 1
    else:
        unmatched += 1

if OUTPUT_FILE.exists():
    raise SystemExit(f"Output already exists: {OUTPUT_FILE}")

OUTPUT_FILE.write_text(
    json.dumps({
        "records_checked": len(results),
        "quote_matches": matched,
        "unmatched": unmatched,
        "records": results,
        "warning": "A quote match does not establish factual correctness or license approval."
    }, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("Records checked:", len(results))
print("Quote matches:", matched)
print("Unmatched:", unmatched)
print("Report:", OUTPUT_FILE)
