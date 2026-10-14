import json
from pathlib import Path
from collections import Counter

path = Path("data/meenaai_12000_candidate_pairs.jsonl")
report_path = Path("data/audit_12000_report.json")

total = 0
valid = 0
missing_q = 0
missing_a = 0
duplicates = 0
seen = set()
sources = Counter()
topics = Counter()
sample = []

with path.open(encoding="utf-8") as f:
    for line in f:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue

        total += 1
        q = str(row.get("question") or row.get("instruction") or "").strip()
        a = str(row.get("answer") or row.get("output") or "").strip()

        if not q:
            missing_q += 1
        if not a:
            missing_a += 1

        if q and a:
            valid += 1
            key = " ".join(q.lower().split())
            if key in seen:
                duplicates += 1
            seen.add(key)

        source = row.get("source_id") or row.get("source") or "UNKNOWN"
        topic = row.get("topic") or row.get("category") or "UNKNOWN"
        sources[str(source)] += 1
        topics[str(topic)] += 1

        if len(sample) < 3:
            sample.append({
                "keys": list(row.keys()),
                "question": q[:250],
                "answer": a[:350],
                "source_id": row.get("source_id"),
                "source": row.get("source"),
                "topic": topic,
            })

report = {
    "total_rows": total,
    "rows_with_question_and_answer": valid,
    "missing_question": missing_q,
    "missing_answer": missing_a,
    "duplicate_questions_after_normalization": duplicates,
    "source_counts": dict(sources),
    "topic_counts": dict(topics.most_common(30)),
    "samples": sample,
    "warning": "Structural audit only; does not establish factual accuracy, licensing, or test-set independence."
}

report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({
    k: v for k, v in report.items()
    if k not in ("source_counts", "topic_counts", "samples")
}, indent=2))
print("\nSOURCE COUNTS:")
print(json.dumps(dict(sources), indent=2))
print("\nSAMPLE RECORDS:")
print(json.dumps(sample, indent=2, ensure_ascii=False))
print(f"\nReport saved: {report_path}")
