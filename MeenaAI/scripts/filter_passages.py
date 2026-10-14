
from pathlib import Path
import json
import re
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "passages.jsonl"
OUTPUT = ROOT / "data" / "eligible_passages.jsonl"
REPORT = ROOT / "data" / "passage_filter_report.json"

# Conservative filters for obvious front matter.
# These are screening rules, not proof that a passage is useful.
FRONT_MATTER = [
    r"\ball rights reserved\b",
    r"\bcopyright\b",
    r"\bissn\b",
    r"\bisbn\b",
    r"\bpreparation of this document\b",
    r"\bcover photographs?\b",
    r"\bcover design\b",
    r"\btable of contents\b",
    r"\blist of figures\b",
    r"\blist of tables\b",
    r"\bforeword\b",
    r"\backnowledg(e)?ments\b",
    r"\bfor further information\b",
]

def is_front_matter(text):
    text_lower = text.lower()
    hits = sum(bool(re.search(pattern, text_lower))
               for pattern in FRONT_MATTER)
    # Require multiple indicators to avoid discarding a useful
    # technical passage merely because it mentions copyright.
    return hits >= 2

records = []
with INPUT.open(encoding="utf-8") as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

kept = []
review = []
reason_counts = Counter()

for record in records:
    text = record.get("text", "")
    words = text.split()

    if len(words) < 80:
        review.append({
            **record,
            "review_reason": "short_passage"
        })
        reason_counts["short_passage"] += 1
    elif is_front_matter(text):
        review.append({
            **record,
            "review_reason": "possible_front_matter"
        })
        reason_counts["possible_front_matter"] += 1
    else:
        kept.append(record)

with OUTPUT.open("w", encoding="utf-8") as f:
    for record in kept:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

# Keep rejected/flagged material for manual review instead of deleting it.
REVIEW = ROOT / "data" / "passages_needing_review.jsonl"
with REVIEW.open("w", encoding="utf-8") as f:
    for record in review:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

report = {
    "input_passages": len(records),
    "eligible_for_next_review": len(kept),
    "flagged_for_manual_review": len(review),
    "flag_reasons": dict(reason_counts),
    "warning": (
        "Eligible passages still require human/content-quality review. "
        "They are not automatically approved for Q&A generation."
    ),
}

REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
print(f"\nCreated: {OUTPUT}")
print(f"Created: {REVIEW}")
print(f"Created: {REPORT}")
