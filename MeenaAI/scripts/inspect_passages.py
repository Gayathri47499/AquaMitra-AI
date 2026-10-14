
from pathlib import Path
import json
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "passages.jsonl"
OUT = ROOT / "data" / "passage_audit.json"

records = []
with PATH.open(encoding="utf-8") as f:
    for line_no, line in enumerate(f, 1):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"Invalid JSON on line {line_no}")

source_counts = Counter(r.get("source_id", "MISSING") for r in records)
word_counts = [len(r.get("text", "").split()) for r in records]
short = [r for r in records if len(r.get("text", "").split()) < 80]
missing = [
    r for r in records
    if not r.get("source_id") or not r.get("text")
    or not r.get("page_start") or not r.get("page_end")
]

report = {
    "total_passages": len(records),
    "unique_sources": len(source_counts),
    "word_count_min": min(word_counts, default=0),
    "word_count_max": max(word_counts, default=0),
    "word_count_average": round(sum(word_counts) / len(word_counts), 2)
        if word_counts else 0,
    "passages_under_80_words": len(short),
    "records_missing_required_fields": len(missing),
    "passages_per_source": dict(sorted(source_counts.items())),
}

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))

print("\n--- SAMPLE PASSAGES ---")
for record in records[:3]:
    print("\n", record["passage_id"])
    print(record["text"][:700])
    print("-" * 60)

print("\nAudit saved to:", OUT)
