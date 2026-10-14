
from pathlib import Path
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

MERGED = DATA / "merged_candidates.jsonl"
PASSAGES = DATA / "eligible_passages.jsonl"

CLEAN = DATA / "quality_screened_candidates.jsonl"
REVIEW = DATA / "quality_needs_review.jsonl"
REPORT = DATA / "quality_report.json"

# Avoid accidentally overwriting previous results.
for path in (CLEAN, REVIEW, REPORT):
    if path.exists():
        raise SystemExit(
            f"{path.name} already exists. Rename it before rerunning."
        )


def read_jsonl(path):
    if not path.exists():
        raise SystemExit(f"Missing input file: {path}")

    rows = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Warning: invalid JSON at {path.name}:{line_no}")
    return rows


def normalize(text):
    text = str(text or "").casefold()
    return re.sub(r"\s+", " ", text).strip()


def quote_is_supported(quote, passage_text):
    quote = normalize(quote)
    passage_text = normalize(passage_text)

    if len(quote) < 15:
        return False

    # Exact normalized substring check; not a full factual verification.
    return quote in passage_text


rows = read_jsonl(MERGED)
passages = read_jsonl(PASSAGES)

passage_map = {
    row.get("passage_id"): row.get("text", "")
    for row in passages
    if row.get("passage_id")
}

print("Merged candidates:", len(rows))
print("Passages available for evidence checks:", len(passage_map))

reasons = Counter()
review_rows = []
screened_rows = []

# First-pass structural and evidence checks.
for row in rows:
    q = str(row.get("question") or "").strip()
    a = str(row.get("answer") or "").strip()
    provenance = row.get("provenance", "")
    problems = []

    if len(q) < 12:
        problems.append("question_too_short")

    if len(a) < 30:
        problems.append("answer_too_short")

    if q.casefold() == a.casefold():
        problems.append("question_equals_answer")

    if provenance == "MeenaAI_PDF_GENERATION":
        passage_id = row.get("passage_id")
        quote = row.get("evidence_quote", "")
        passage_text = passage_map.get(passage_id, "")

        if not passage_text:
            problems.append("source_passage_missing")
        elif not quote_is_supported(quote, passage_text):
            problems.append("evidence_quote_not_found")

        # These generated examples still need factual review.
        row["quality_status"] = "NEEDS_FACTUAL_REVIEW"

    else:
        # External examples have no source passage/evidence quote here.
        row["quality_status"] = "EXTERNAL_UNVERIFIED"
        problems.append("external_answer_needs_source_review")

    if problems:
        row["quality_flags"] = problems
        review_rows.append(row)
        for problem in problems:
            reasons[problem] += 1
    else:
        row["quality_flags"] = []
        screened_rows.append(row)

print("Structurally screened:", len(screened_rows))
print("Flagged for review:", len(review_rows))

# Find near-duplicate questions among structurally screened records.
# This is a conservative review flag, not automatic factual rejection.
near_duplicate_count = 0

if len(screened_rows) > 1:
    questions = [normalize(r["question"]) for r in screened_rows]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        max_features=100000,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(questions)

    nn = NearestNeighbors(
        metric="cosine",
        algorithm="brute",
        n_neighbors=2,
        n_jobs=-1,
    )
    nn.fit(matrix)

    distances, indices = nn.kneighbors(matrix)

    duplicate_indices = set()

    for i in range(len(screened_rows)):
        j = int(indices[i][1])
        similarity = 1.0 - float(distances[i][1])

        if i != j and similarity >= 0.92:
            # Keep the earlier record as the provisional representative.
            if i > j:
                duplicate_indices.add(i)

    if duplicate_indices:
        new_screened = []

        for i, row in enumerate(screened_rows):
            if i in duplicate_indices:
                row["quality_status"] = "NEAR_DUPLICATE_REVIEW"
                row["quality_flags"] = ["question_similarity_at_least_0.92"]
                review_rows.append(row)
                near_duplicate_count += 1
            else:
                new_screened.append(row)

        screened_rows = new_screened

# Write separate outputs; do not overwrite the merged candidates.
with CLEAN.open("w", encoding="utf-8") as f:
    for row in screened_rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

with REVIEW.open("w", encoding="utf-8") as f:
    for row in review_rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

report = {
    "input_rows": len(rows),
    "structurally_screened_rows": len(screened_rows),
    "rows_needing_review": len(review_rows),
    "near_duplicate_rows_flagged": near_duplicate_count,
    "review_reason_counts": dict(reasons),
    "screened_output": str(CLEAN),
    "review_output": str(REVIEW),
    "important_limitations": [
        "Screening does not establish factual correctness.",
        "External dataset licensing and provenance remain unverified.",
        "Similarity detection uses question text and may miss paraphrases.",
        "Rows in the screened file are not yet approved for model training.",
    ],
}

REPORT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nQuality screening complete.")
print(json.dumps(report, indent=2))
