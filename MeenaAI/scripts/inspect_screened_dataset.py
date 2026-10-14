
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "data" / "quality_screened_candidates.jsonl"

def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

rows = load_jsonl(INPUT)

print("=" * 60)
print("MEENAAI SCREENED DATASET INSPECTION")
print("=" * 60)
print("Total records:", len(rows))

print("\nPROVENANCE")
for key, count in Counter(
    r.get("provenance", "MISSING") for r in rows
).most_common():
    print(f"{key}: {count}")

print("\nLICENSE STATUS")
for key, count in Counter(
    r.get("license_status", "MISSING") for r in rows
).most_common():
    print(f"{key}: {count}")

print("\nTOPICS")
for key, count in Counter(
    r.get("topic") or "UNASSIGNED" for r in rows
).most_common(25):
    print(f"{key}: {count}")

print("\nSPECIES")
for key, count in Counter(
    r.get("species") or "UNASSIGNED" for r in rows
).most_common(20):
    print(f"{key}: {count}")

print("\nSAMPLE RECORDS")
for i, row in enumerate(rows[:10], start=1):
    print(f"\n--- Record {i} ---")
    print("Source:", row.get("source_id"))
    print("Question:", row.get("question", "")[:500])
    print("Answer:", row.get("answer", "")[:800])
    print("Evidence:", row.get("evidence_quote", "")[:300])
    print("Status:", row.get("candidate_status"))

print("\nINSPECTION COMPLETE")
print("This report does not establish factual correctness.")
