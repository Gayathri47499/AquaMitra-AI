
import json
from pathlib import Path
from collections import Counter

root = Path(__file__).resolve().parents[1]
source = root / "data" / "meenaai_12000_candidate_pairs.jsonl"
report = root / "data" / "dataset_quality_report.json"

rows = []
with source.open("r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            rows.append(json.loads(line))

def get_text(row, keys):
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""

seen = set()
duplicate_questions = 0
missing_fields = 0
external_count = 0
internal_count = 0
valid_rows = 0

for row in rows:
    question = get_text(row, ["question"])
    answer = get_text(row, ["answer", "response"])

    if not question or not answer:
        missing_fields += 1
        continue

    key = " ".join(question.lower().split())
    if key in seen:
        duplicate_questions += 1
    else:
        seen.add(key)

    valid_rows += 1

    if row.get("dataset_origin") == "AQUA_external_test_split":
        external_count += 1
    else:
        internal_count += 1

result = {
    "total_rows": len(rows),
    "rows_with_question_and_answer": valid_rows,
    "missing_question_or_answer": missing_fields,
    "duplicate_questions": duplicate_questions,
    "internal_generated_rows": internal_count,
    "external_test_split_rows": external_count,
    "verified_rows": 0,
    "training_ready": False,
    "note": "Structural checks do not verify factual accuracy, aquaculture relevance, licensing, or benchmark contamination."
}

report.write_text(
    json.dumps(result, indent=2),
    encoding="utf-8"
)

print(json.dumps(result, indent=2))
print(f"\nReport saved to: {report}")
