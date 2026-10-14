import csv
import json
from pathlib import Path
from collections import Counter

root = Path(__file__).resolve().parent.parent
data_dir = root / "data"

approved = set()
with (root / "sources" / "sources.csv").open(
    encoding="utf-8-sig", newline=""
) as f:
    for row in csv.DictReader(f):
        if (
            row.get("status", "").strip() == "PRODUCT_APPROVED"
            and row.get("commercial_use", "").strip().lower() == "yes"
            and row.get("allowed_in_product", "").strip().lower() == "yes"
        ):
            approved.add(row["source_id"].strip())

source = data_dir / "meenaai_training_candidates.jsonl"
output = data_dir / "product_candidate_review.jsonl"
counts = Counter()
written = 0

with source.open(encoding="utf-8") as inp, output.open("w", encoding="utf-8") as out:
    for line in inp:
        if not line.strip():
            continue
        row = json.loads(line)
        sid = row.get("source_id", "")
        if sid in approved:
            row["product_source_registry_status"] = "PRODUCT_APPROVED_REQUIRES_LICENSE_CONFIRMATION"
            row["training_eligible"] = False
            row["training_blocker"] = "FACTUAL_REVIEW_PENDING"
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
            counts[sid] += 1

print("Registry-approved source IDs:", sorted(approved))
print("Candidate rows selected:", written)
print("Counts by source:")
for sid, count in sorted(counts.items()):
    print(f"  {sid}: {count}")
print("Output:", output)
print("Training eligible: 0 until factual review and license confirmation")
