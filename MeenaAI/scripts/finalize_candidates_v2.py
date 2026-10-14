
import json
import re
import unicodedata
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CANDIDATES = DATA / "qa_candidates.jsonl"
PASSAGES = DATA / "eligible_passages.jsonl"

OUTPUT = DATA / "deduplicated_candidates_v2.jsonl"
REVIEW = DATA / "source_review_required_v2.jsonl"
REPORT = DATA / "finalization_report_v2.json"

def read_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def normalize(text):
    text = unicodedata.normalize("NFKC", str(text or "")).casefold()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())

def quote_matches(quote, source):
    # Support excerpts where ... indicates omitted text.
    parts = re.split(r"\.{3,}|…|\[\s*\.\.\.\s*\]", str(quote or ""))
    parts = [normalize(p) for p in parts if normalize(p)]

    source_text = normalize(source)
    if not parts:
        return False

    # A single continuous quote must match exactly after normalization.
    if len(parts) == 1:
        return len(parts[0]) >= 15 and parts[0] in source_text

    # For omitted text, each excerpt must occur in source order.
    # Requiring meaningful fragments reduces accidental matches.
    position = 0
    for part in parts:
        if len(part) < 12:
            return False
        found = source_text.find(part, position)
        if found < 0:
            return False
        position = found + len(part)

    return True

for path in (OUTPUT, REVIEW, REPORT):
    if path.exists():
        raise SystemExit(f"Output already exists: {path}")

candidates = read_jsonl(CANDIDATES)
passages = read_jsonl(PASSAGES)
passage_map = {p.get("passage_id"): p for p in passages}

accepted, review = [], []
reasons = Counter()
seen = set()

for original in candidates:
    row = dict(original)
    flags = []

    question = str(row.get("question", "")).strip()
    answer = str(row.get("answer", "")).strip()
    quote = str(row.get("evidence_quote", "")).strip()
    pid = row.get("passage_id")
    passage = passage_map.get(pid)

    if len(question) < 12:
        flags.append("question_missing_or_too_short")
    if len(answer) < 20:
        flags.append("answer_missing_or_too_short")
    if len(quote) < 15:
        flags.append("evidence_quote_missing_or_too_short")

    if passage is None:
        flags.append("passage_id_not_found")
    elif row.get("source_id") != passage.get("source_id"):
        flags.append("source_id_mismatch")
    elif not quote_matches(quote, passage.get("text", "")):
        flags.append("evidence_quote_not_found")

    key = (str(pid), normalize(question))
    if key in seen:
        flags.append("duplicate_question_for_passage")
    seen.add(key)

    row["quality_flags"] = flags
    row["candidate_status"] = (
        "SOURCE_MATCH_REQUIRES_FACTUAL_AND_LICENSE_REVIEW"
        if not flags else "NEEDS_REVIEW"
    )

    if flags:
        review.append(row)
        reasons.update(flags)
    else:
        accepted.append(row)

for path, rows in ((OUTPUT, accepted), (REVIEW, review)):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

report = {
    "input_candidates": len(candidates),
    "source_matched_candidates": len(accepted),
    "candidates_needing_review": len(review),
    "review_flag_counts": dict(reasons),
    "warning": (
        "Source matching is not factual verification or license approval."
    )
}

REPORT.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(json.dumps(report, ensure_ascii=False, indent=2))
print("Matched file:", OUTPUT)
print("Review file:", REVIEW)
print("Report:", REPORT)
