
from pathlib import Path
from datasets import load_dataset
import json

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATASET_ID = "KurmaAI/AQUA-Test-Dataset"
SPLIT = "test"

OUTPUT = DATA_DIR / "external_aqua_raw.jsonl"
REPORT = DATA_DIR / "external_aqua_report.json"

print("Loading cached/downloaded dataset...")
dataset = load_dataset(DATASET_ID, split=SPLIT)

print("Rows:", len(dataset))
print("Columns:", dataset.column_names)

required = {"question", "response"}
if not required.issubset(set(dataset.column_names)):
    raise SystemExit(
        f"Unexpected schema. Expected {required}; got {dataset.column_names}"
    )

# Refuse to overwrite an earlier export.
if OUTPUT.exists():
    raise SystemExit(
        f"{OUTPUT} already exists. Rename or back it up before exporting again."
    )

count = 0
with OUTPUT.open("w", encoding="utf-8") as f:
    for index, row in enumerate(dataset):
        record = {
            "external_id": f"AQUA-TEST-{index + 1:05d}",
            "question": str(row.get("question") or "").strip(),
            "answer": str(row.get("response") or "").strip(),
            "dataset_id": DATASET_ID,
            "dataset_split": SPLIT,
            "license_status": "UNVERIFIED",
            "candidate_status": "UNREVIEWED",
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        count += 1

report = {
    "dataset_id": DATASET_ID,
    "split": SPLIT,
    "input_rows": len(dataset),
    "exported_rows": count,
    "original_columns": dataset.column_names,
    "license_status": "UNVERIFIED",
    "usage_warning": (
        "Split is named test. Do not use for training until intended use, "
        "provenance, licensing, and evaluation leakage are reviewed."
    ),
    "export_file": str(OUTPUT),
}

REPORT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\nExport complete.")
print("Exported rows:", count)
print("Raw dataset:", OUTPUT)
print("Metadata report:", REPORT)
print("Original dataset fields preserved; no cleaning or merging performed.")
