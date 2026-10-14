
from pathlib import Path
import json
import re
import hashlib
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)

INTERNAL = DATA / "qa_candidates.jsonl"
EXTERNAL = DATA / "external_aqua_raw.jsonl"

MERGED = DATA / "merged_candidates.jsonl"
REJECTED = DATA / "merge_rejected.jsonl"
REPORT = DATA / "merge_report.json"

# Prevent accidental overwrites.
for path in (MERGED, REJECTED, REPORT):
    if path.exists():
        raise SystemExit(
            f"{path.name} already exists. Back it up or rename it before rerunning."
        )


def read_jsonl(path):
    if not path.exists():
        raise SystemExit(f"Required input not found: {path}")

    rows = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Skipping malformed JSON: {path.name}, line {line_no}")
    return rows


def normalize(text):
    text = str(text or "").casefold()
    return re.sub(r"\s+", " ", text).strip()


def has_aquaculture_context(question, answer):
    # Conservative keyword screen only; human review is still needed.
    text = f"{question} {answer}".casefold()
    terms = [
        "aquaculture", "fish farm", "fish farming", "shrimp",
        "prawn", "tilapia", "catfish", "fingerling", "hatchery",
        "pond", "fish feed", "stocking density", "water quality",
        "dissolved oxygen", "biosecurity", "fish disease",
        "white spot syndrome", "ras farming", "recirculating aquaculture",
        "farm-gate", "fish harvest", "fish pond", "aquatic"
    ]
    return any(term in text for term in terms)


def record_hash(question, answer):
    raw = normalize(question) + "\n" + normalize(answer)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


internal_rows = read_jsonl(INTERNAL)
external_rows = read_jsonl(EXTERNAL)

candidates = []
rejected = []
counts = Counter()

for row in internal_rows:
    question = str(row.get("question") or "").strip()
    answer = str(row.get("answer") or "").strip()

    candidate = {
        "question": question,
        "answer": answer,
        "source_id": row.get("source_id"),
        "passage_id": row.get("passage_id"),
        "page_start": row.get("page_start"),
        "page_end": row.get("page_end"),
        "topic": row.get("topic", "other"),
        "species": row.get("species", "general"),
        "evidence_quote": row.get("evidence_quote", ""),
        "language": row.get("language", "en"),
        "license_status": "SOURCE_REVIEW_REQUIRED",
        "provenance": "MeenaAI_PDF_GENERATION",
        "candidate_status": "UNVERIFIED",
    }
    candidates.append(candidate)

for row in external_rows:
    question = str(row.get("question") or "").strip()
    answer = str(row.get("answer") or "").strip()

    candidate = {
        "question": question,
        "answer": answer,
        "source_id": row.get("dataset_id", "KurmaAI/AQUA-Test-Dataset"),
        "passage_id": None,
        "page_start": None,
        "page_end": None,
        "topic": "other",
        "species": "general",
        "evidence_quote": "",
        "language": "en",
        "license_status": "UNVERIFIED",
        "provenance": row.get("dataset_id", "external_dataset"),
        "external_id": row.get("external_id"),
        "candidate_status": "UNREVIEWED",
    }
    candidates.append(candidate)

seen = set()

with MERGED.open("w", encoding="utf-8") as out:
    for row in candidates:
        q = row["question"]
        a = row["answer"]

        reason = None
        if len(q) < 12:
            reason = "question_empty_or_too_short"
        elif len(a) < 30:
            reason = "answer_empty_or_too_short"
        elif not has_aquaculture_context(q, a):
            reason = "aquaculture_keyword_screen_failed"

        key = record_hash(q, a)

        if reason:
            row["rejection_reason"] = reason
            rejected.append(row)
            counts[reason] += 1
            continue

        if key in seen:
            row["rejection_reason"] = "exact_question_answer_duplicate"
            rejected.append(row)
            counts["exact_question_answer_duplicate"] += 1
            continue

        seen.add(key)
        out.write(json.dumps(row, ensure_ascii=False) + "\n")

with REJECTED.open("w", encoding="utf-8") as out:
    for row in rejected:
        out.write(json.dumps(row, ensure_ascii=False) + "\n")

report = {
    "internal_input_rows": len(internal_rows),
    "external_input_rows": len(external_rows),
    "total_input_rows": len(candidates),
    "merged_candidate_rows": len(seen),
    "rejected_rows": len(rejected),
    "rejection_reasons": dict(counts),
    "warning": (
        "Keyword screening is not factual validation. Near-duplicates, "
        "answer accuracy, provenance, and licenses still require review. "
        "Do not use the merged file for training yet."
    ),
    "merged_file": str(MERGED),
    "rejected_file": str(REJECTED),
}

REPORT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nMerge candidate stage complete.")
print(json.dumps(report, indent=2))
