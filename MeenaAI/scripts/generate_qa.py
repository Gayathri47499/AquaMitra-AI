
from pathlib import Path
from dotenv import load_dotenv
from google import genai
import json
import os
import re
import time
import unicodedata

# ============================================================
# MEENAAI AQUACULTURE Q&A GENERATOR
# Safe resume + duplicate prevention + retry handling
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

INPUT = ROOT / "data" / "eligible_passages.jsonl"
OUTPUT = ROOT / "data" / "qa_candidates.jsonl"
ERRORS = ROOT / "data" / "qa_generation_errors.jsonl"
MANIFEST = ROOT / "data" / "qa_processed_passages.jsonl"

QUESTIONS_PER_PASSAGE = 8
BATCH_SIZE = 3
MAX_PASSAGES = 0                 # 0 = process all missing passages
MAX_RETRIES = 4
REQUEST_PAUSE_SECONDS = 1

if not API_KEY:
    raise SystemExit("GEMINI_API_KEY missing from root .env file.")

if not INPUT.exists():
    raise SystemExit(f"Input file not found: {INPUT}")

client = genai.Client(api_key=API_KEY)


def read_jsonl(path):
    if not path.exists():
        return []

    records = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Warning: invalid JSON in {path.name}, line {line_no}")
    return records


def append_jsonl(path, records):
    if not records:
        return

    with path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def normalize(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def question_key(passage_id, question):
    return (str(passage_id), normalize(question))


def extract_json(text):
    if not text or not text.strip():
        raise ValueError("Model returned empty output.")

    cleaned = text.strip()
    cleaned = re.sub(
        r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE
    )
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise ValueError("No valid JSON object in model response.")


def build_prompt(batch):
    source_blocks = []

    for p in batch:
        source_blocks.append(
            f"""
PASSAGE_ID: {p['passage_id']}
SOURCE_ID: {p['source_id']}
PAGES: {p.get('page_start', '')}-{p.get('page_end', '')}
TEXT:
{p['text']}
"""
        )

    return f"""
You generate candidate Q&A data for MeenaAI, an aquaculture guidance assistant.

Create UP TO {QUESTIONS_PER_PASSAGE} useful, distinct question-answer pairs
for EACH supplied passage. Do not force questions when evidence is insufficient.

STRICT RULES:
1. Use only facts explicitly supported by the same passage.
2. Never invent figures, costs, treatments, diagnoses, or dosages.
3. Ignore acknowledgements, references, copyright pages, and metadata.
4. Keep questions specifically relevant to aquaculture.
5. Do not combine facts from different passages.
6. Preserve numbers and units as written in the source.
7. Include a short exact evidence quote for each answer.
8. Use the exact passage_id supplied with the passage.
9. Avoid duplicate questions and superficial paraphrases.
10. Return valid JSON only.

Required structure:
{{
  "items": [
    {{
      "passage_id": "exact passage ID",
      "question": "question",
      "answer": "source-supported answer",
      "topic": "feeding|water_quality|fish_health|pond_management|species|biosecurity|economics|safety|other",
      "species": "species name or general",
      "difficulty": "easy|medium|hard",
      "evidence_quote": "exact short excerpt from the passage"
    }}
  ]
}}

PASSAGES:
{chr(10).join(source_blocks)}
"""


# ------------------------------------------------------------
# LOAD INPUTS AND RESUME STATE
# ------------------------------------------------------------

passages = read_jsonl(INPUT)
manifest_rows = read_jsonl(MANIFEST)
existing_candidates = read_jsonl(OUTPUT)

# Only the explicit manifest determines whether a passage
# has completed generation. Candidate presence alone does not.
completed = {
    row["passage_id"]
    for row in manifest_rows
    if row.get("passage_id")
}

# Avoid appending exact question duplicates already in the file.
existing_question_keys = {
    question_key(row.get("passage_id"), row.get("question"))
    for row in existing_candidates
    if row.get("passage_id") and row.get("question")
}

# Retry passages absent from the manifest, including the six
# passages previously skipped by the old resume logic.
todo = [
    p for p in passages
    if p.get("passage_id") and p["passage_id"] not in completed
]

if MAX_PASSAGES > 0:
    todo = todo[:MAX_PASSAGES]

print("=" * 60)
print("MEENAAI Q&A GENERATION")
print("=" * 60)
print("Eligible passages:", len(passages))
print("Manifest-completed passages:", len(completed))
print("Existing candidate rows:", len(existing_candidates))
print("Passages to process:", len(todo))
print("Model:", MODEL)
print("Batch size:", BATCH_SIZE)
print("Maximum questions per passage:", QUESTIONS_PER_PASSAGE)

if not todo:
    print("\nNothing to process. All passage IDs are in the manifest.")
    raise SystemExit(0)


# ------------------------------------------------------------
# GENERATE IN SMALL BATCHES
# ------------------------------------------------------------

new_candidate_count = 0
successful_passages = 0
failed_passages = 0

for start in range(0, len(todo), BATCH_SIZE):
    batch = todo[start:start + BATCH_SIZE]
    passage_by_id = {p["passage_id"]: p for p in batch}
    batch_ids = set(passage_by_id)

    accepted = None
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = client.interactions.create(
                model=MODEL,
                input=build_prompt(batch),
            )

            data = extract_json(getattr(result, "output_text", None))

            if not isinstance(data, dict) or not isinstance(
                data.get("items"), list
            ):
                raise ValueError("Response must contain an items list.")

            # First validate items and identify passages for which
            # the model actually returned usable Q&A.
            valid_items = []
            returned_passage_ids = set()

            for item in data["items"]:
                if not isinstance(item, dict):
                    continue

                pid = item.get("passage_id")
                if pid not in batch_ids:
                    continue

                question = str(item.get("question", "")).strip()
                answer = str(item.get("answer", "")).strip()
                evidence = str(item.get("evidence_quote", "")).strip()

                if not question or not answer or not evidence:
                    continue

                returned_passage_ids.add(pid)
                valid_items.append({
                    "passage_id": pid,
                    "question": question,
                    "answer": answer,
                    "topic": item.get("topic", "other"),
                    "species": item.get("species", "general"),
                    "difficulty": item.get("difficulty", "medium"),
                    "evidence_quote": evidence,
                })

            accepted = (valid_items, returned_passage_ids)
            break

        except Exception as exc:
            last_error = str(exc)

            print(
                f"\nBatch {start // BATCH_SIZE + 1}, "
                f"attempt {attempt}/{MAX_RETRIES} failed: {last_error}"
            )

            if attempt < MAX_RETRIES:
                wait = min(5 * (2 ** (attempt - 1)), 30)
                print(f"Retrying in {wait} seconds...")
                time.sleep(wait)

    if accepted is None:
        append_jsonl(ERRORS, [{
            "passage_ids": sorted(batch_ids),
            "error": last_error or "Unknown generation error",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }])
        failed_passages += len(batch)
        print("Batch failed; these passages remain eligible for retry.")
        continue

    valid_items, returned_passage_ids = accepted
    new_rows = []
    batch_question_keys = set()

    for item in valid_items:
        pid = item["passage_id"]
        key = question_key(pid, item["question"])

        if key in existing_question_keys or key in batch_question_keys:
            continue

        p = passage_by_id[pid]

        new_rows.append({
            "passage_id": pid,
            "source_id": p["source_id"],
            "page_start": p.get("page_start"),
            "page_end": p.get("page_end"),
            "question": item["question"],
            "answer": item["answer"],
            "topic": item["topic"],
            "species": item["species"],
            "difficulty": item["difficulty"],
            "evidence_quote": item["evidence_quote"],
            "candidate_status": "UNVERIFIED",
            "language": "en",
        })

        batch_question_keys.add(key)

    # Save candidates before writing manifest entries.
    append_jsonl(OUTPUT, new_rows)

    for row in new_rows:
        existing_question_keys.add(
            question_key(row["passage_id"], row["question"])
        )

    # Only mark a passage complete if the model returned at least
    # one usable Q&A for that passage. Missing passages can retry.
    completed_now = sorted(returned_passage_ids)

    append_jsonl(MANIFEST, [
        {
            "passage_id": pid,
            "candidate_count": sum(
                1 for row in new_rows if row["passage_id"] == pid
            ),
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for pid in completed_now
    ])

    successful_passages += len(completed_now)
    failed_this_batch = batch_ids - returned_passage_ids
    failed_passages += len(failed_this_batch)

    if failed_this_batch:
        append_jsonl(ERRORS, [{
            "passage_ids": sorted(failed_this_batch),
            "error": "No usable Q&A returned for these passages.",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }])

    new_candidate_count += len(new_rows)

    print(
        f"Batch {start // BATCH_SIZE + 1}: "
        f"{len(new_rows)} new candidates; "
        f"{len(completed_now)}/{len(batch)} passages completed"
    )

    time.sleep(REQUEST_PAUSE_SECONDS)


# ------------------------------------------------------------
# FINAL SUMMARY
# ------------------------------------------------------------

final_candidates = read_jsonl(OUTPUT)
final_manifest = read_jsonl(MANIFEST)

final_completed_ids = {
    row["passage_id"]
    for row in final_manifest
    if row.get("passage_id")
}

remaining = [
    p for p in passages
    if p.get("passage_id") and p["passage_id"] not in final_completed_ids
]

print("\n" + "=" * 60)
print("GENERATION RUN COMPLETE")
print("=" * 60)
print("New candidates added:", new_candidate_count)
print("Total candidate rows:", len(final_candidates))
print("Unique passage IDs in manifest:", len(final_completed_ids))
print("Passages still needing generation:", len(remaining))
print("Passage processing errors this run:", failed_passages)
print("Candidates:", OUTPUT)
print("Manifest:", MANIFEST)
print("Errors:", ERRORS)
print("\nAll generated Q&A remain UNVERIFIED.")
