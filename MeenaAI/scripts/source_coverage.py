
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

def read_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

passages = read_jsonl(DATA / "eligible_passages.jsonl")
candidates = read_jsonl(DATA / "qa_candidates.jsonl")

passage_counts = Counter(p.get("source_id", "UNKNOWN") for p in passages)
qa_counts = Counter(q.get("source_id", "UNKNOWN") for q in candidates)

print("=" * 60)
print("MEENAAI SOURCE COVERAGE")
print("=" * 60)
print("Eligible passages:", len(passages))
print("Q&A candidate rows:", len(candidates))
print("Distinct source IDs:", len(passage_counts))

print("\nPASSAGES AND CANDIDATES PER SOURCE")
for source_id, count in sorted(passage_counts.items()):
    print(
        f"{source_id}: {count} passages, "
        f"{qa_counts.get(source_id, 0)} Q&A candidates"
    )

print("\nQ&A CANDIDATES WITHOUT AN ELIGIBLE PASSAGE SOURCE")
for source_id, count in sorted(qa_counts.items()):
    if source_id not in passage_counts:
        print(f"{source_id}: {count} candidates")

print("\nCoverage report complete.")
