import json
from pathlib import Path
from collections import Counter

src = Path("data/meenaai_12000_candidate_pairs.jsonl")
dst = Path("data/meenaai_expanded_provisional.jsonl")

# Only sources marked for product use in the source registry.
registry = Path("sources/sources.csv")
import csv

approved = set()
with registry.open(encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        sid = (r.get("source_id") or "").strip()
        status = (r.get("commercial_status") or r.get("license_status") or "").strip().upper()
        allowed = (r.get("allowed_in_product") or "").strip().lower()
        if sid and ("PRODUCT_APPROVED" in status or allowed == "yes"):
            approved.add(sid)

rows, seen = [], set()
rejected = Counter()

with src.open(encoding="utf-8") as f:
    for line in f:
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            rejected["invalid_json"] += 1
            continue

        q = str(r.get("question") or "").strip()
        a = str(r.get("answer") or "").strip()
        sid = str(r.get("source_id") or "").strip()

        if not q or not a:
            rejected["missing_question_or_answer"] += 1
            continue
        if sid not in approved:
            rejected["source_not_approved_by_registry"] += 1
            continue

        key = " ".join(q.lower().split())
        if key in seen:
            rejected["duplicate_question"] += 1
            continue
        seen.add(key)

        rows.append({
            "question": q,
            "answer": a,
            "source_id": sid,
            "evidence_quote": r.get("evidence_quote", ""),
            "topic": r.get("topic", ""),
            "status": "PROVISIONAL_NOT_FACTUALLY_VERIFIED"
        })

with dst.open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print("Registry-approved source IDs:", sorted(approved))
print("Expanded provisional rows:", len(rows))
print("Rows by source:", dict(Counter(r["source_id"] for r in rows)))
print("Rejected:", dict(rejected))
print("Saved:", dst)
print("IMPORTANT: registry approval is not independent legal or factual verification.")
