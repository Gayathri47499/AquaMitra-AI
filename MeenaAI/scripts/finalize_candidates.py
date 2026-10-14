
import json
import re
import hashlib
import unicodedata
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CANDIDATES = DATA / "qa_candidates.jsonl"
PASSAGES = DATA / "eligible_passages.jsonl"

OUTPUT = DATA / "deduplicated_candidates.jsonl"
REVIEW = DATA / "source_review_required.jsonl"
REPORT = DATA / "finalization_report.json"

def read_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def norm(text):
    text = unicodedata.normalize("NFKC", str(text or "")).casefold()
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def quote_norm(text):
    text = norm(text)
    return re.sub(r"[^\w\s]", "", text)

for path in (OUTPUT, REVIEW, REPORT):
    if path.exists():
        raise SystemExit(
            f"Output already exists: {path}\n"
            "Rename the existing output before rerunning."
        )

candidates = read_jsonl(CANDIDATES)
passages = read_jsonl(PASSAGES)

passage_by_id = {
    p.get("passage_id"): p for p in passages if p.get("passage_id")
}

seen_questions = set()
accepted = []
review = []
reasons = Counter()

for row in candidates:
    q = str(row.get("question", "")).strip()
    a = str(row.get("answer", "")).strip()
    quote = str(row.get("evidence_quote", "")).strip()
    pid = row.get("passage_id")

    flags = []
    passage = passage_by_id.get(pid)

    if not q or len(q) < 12:
        flags.append("question_missing_or_too_short")

    if not a or len(a) < 20:
        flags.append("answer_missing_or_too_short")

    if not quote or len(quote) < 15:
        flags.append("evidence_quote_missing_or_too_short")

    if not passage:
        flags.append("passage_id_not_found")
    elif row.get("source_id") != passage.get("source_id"):
        flags.append("source_id_mismatch")
    else:
        source_text = quote_norm(passage.get("text", ""))
        normalized_quote = quote_norm(quote)
        if not normalized_quote or normalized_quote not in source_text:
            flags.append("evidence_quote_not_found")

    key = (str(pid), norm(q))
    if key in seen_questions:
        flags.append("duplicate_question_for_passage")
    else:
        seen_questions.add(key)

    # All records still require factual and licensing review.
    row = dict(row)
    row["quality_flags"] = flags
    row["candidate_status"] = (
        "SOURCE_MATCH_REQUIRES_FACTUAL_AND_LICENSE_REVIEW"
        if not flags
        else "NEEDS_REVIEW"
    )

    if flags:
        review.append(row)
        reasons.update(flags)
    else:
        accepted.append(row)

with OUTPUT.open("w", encoding="utf-8") as f:
    for row in accepted:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

with REVIEW.open("w", encoding="utf-8") as f:
    for row in review:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

report = {
    "input_candidates": len(candidates),
    "eligible_passages": len(passages),
    "source_match_candidates": len(accepted),
    "candidates_needing_review": len(review),
    "review_flag_counts": dict(reasons),
    "note": (
        "A source quote match does not prove the answer is factually correct. "
        "All rows require license review before training."
    )
}

REPORT.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(json.dumps(report, ensure_ascii=False, indent=2))
print("\nSource-matched candidates:", OUTPUT)
print("Review queue:", REVIEW)
print("Report:", REPORT)
