
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

internal_file = DATA / "qa_candidates.jsonl"
external_file = DATA / "external_aqua_raw.jsonl"
output_file = DATA / "meenaai_12000_candidate_pairs.jsonl"

def read_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

internal = read_jsonl(internal_file)
external = read_jsonl(external_file)

TARGET = 12000
internal = internal[:TARGET]
needed_external = TARGET - len(internal)

if needed_external < 0:
    internal = internal[:TARGET]
    external_selected = []
else:
    external_selected = external[:needed_external]

rows = []

for row in internal:
    row = dict(row)
    row["dataset_origin"] = "MeenaAI_source_generated"
    row["review_status"] = "NOT_FULLY_VERIFIED"
    rows.append(row)

for row in external_selected:
    row = dict(row)
    row["dataset_origin"] = "AQUA_external_test_split"
    row["review_status"] = "UNVERIFIED_DO_NOT_USE_AS_TRAINING"
    rows.append(row)

with output_file.open("w", encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

print("Candidate dataset created:", output_file)
print("Total rows:", len(rows))
print("MeenaAI-generated rows:", len(internal))
print("External test-split rows:", len(external_selected))
print("Rows still needing verification:",
      sum(r["review_status"] != "VERIFIED" for r in rows))
