import json
import re
import unicodedata
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

def read_jsonl(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def normalize(text):
    text = unicodedata.normalize("NFKC", str(text or "")).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text)).strip()

candidates = read_jsonl(DATA / "product_candidate_review.jsonl")
passages = read_jsonl(DATA / "eligible_passages.jsonl")

index = {}
for p in passages:
    key = (p.get("source_id"), p.get("passage_id"))
    index.setdefault(key, []).append(p)

def passage_text(p):
    for key in ("text", "passage", "content", "page_text"):
        if p.get(key):
            return str(p[key])
    return ""

report = []
counts = Counter()

for row in candidates:
    key = (row.get("source_id"), row.get("passage_id"))
    matched = index.get(key, [])
    quote = normalize(row.get("evidence_quote", ""))

    quote_found = bool(
        quote and len(quote) >= 15 and
        any(quote in normalize(passage_text(p)) for p in matched)
    )

    status = "QUOTE_MATCH_FOUND_REVIEW_STILL_REQUIRED" if quote_found else "QUOTE_NOT_MATCHED_REVIEW_REQUIRED"
    counts[status] += 1

    report.append({
        "source_id": row.get("source_id"),
        "passage_id": row.get("passage_id"),
        "question": row.get("question"),
        "answer": row.get("answer"),
        "evidence_quote": row.get("evidence_quote"),
        "matching_passage_count": len(matched),
        "quote_match_found": quote_found,
        "audit_status": status,
        "training_eligible": False
    })

out = DATA / "product_evidence_audit.jsonl"
with out.open("w", encoding="utf-8") as f:
    for row in report:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

summary = {
    "candidate_count": len(candidates),
    "passage_count": len(passages),
    "quote_match_found": counts["QUOTE_MATCH_FOUND_REVIEW_STILL_REQUIRED"],
    "quote_not_matched": counts["QUOTE_NOT_MATCHED_REVIEW_REQUIRED"],
    "training_eligible": 0,
    "note": "Quote matches establish traceability only, not answer correctness or license approval."
}
(DATA / "product_evidence_audit_summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)
print(json.dumps(summary, indent=2))
print("Detailed audit:", out)
