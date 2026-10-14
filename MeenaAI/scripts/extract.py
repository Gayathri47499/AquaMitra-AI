
from pathlib import Path
import json
import re
import fitz
import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "sources" / "pdfs"
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Maps PDF filename prefixes to the IDs in license_check.csv.
SOURCE_MAP = {
    "FAO-001": "SRC-001",
    "FAO-002": "SRC-002",
    "FAO-003": "SRC-003",
    "FAO-004": "SRC-004",
    "FAO-005": "SRC-005",
    "WF-001": "SRC-006",
    "WF-002": "SRC-007",
    "WF-003": "SRC-008",
    "AGRODOK-001": "SRC-009",
    "NACA-001": "SRC-010",
    "NACA-002": "SRC-011",
    "NACA-003": "SRC-012",
    "NACA-004": "SRC-013",
    "SRAC-001": "SRC-016",
    "SRAC-002": "SRC-017",
    "SRAC-003": "SRC-018",
    "SRAC-004": "SRC-019",
    "SRAC-005": "SRC-020",
    "SRAC-006": "SRC-021",
}

def clean_text(text):
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

pdf_files = sorted(PDF_DIR.glob("*.pdf"))

if not pdf_files:
    raise SystemExit(f"No PDFs found in: {PDF_DIR}")

raw_pages = []
clean_pages = []
warnings = []
processed_sources = set()

for pdf_path in tqdm(pdf_files, desc="Extracting PDFs"):
    filename = pdf_path.stem

    if filename not in SOURCE_MAP:
        warnings.append(f"Unmapped PDF filename: {pdf_path.name}")
        continue

    source_id = SOURCE_MAP[filename]
    processed_sources.add(source_id)

    try:
        with fitz.open(pdf_path) as doc:
            for page_index, page in enumerate(doc):
                text = page.get_text("text", sort=True)
                raw_record = {
                    "source_id": source_id,
                    "filename": pdf_path.name,
                    "page": page_index + 1,
                    "text": text,
                }
                raw_pages.append(raw_record)

                cleaned = clean_text(text)
                if len(cleaned) < 40:
                    warnings.append(
                        f"Possible scanned/low-text page: "
                        f"{pdf_path.name}, page {page_index + 1}"
                    )

                if cleaned:
                    clean_pages.append({
                        "source_id": source_id,
                        "filename": pdf_path.name,
                        "page": page_index + 1,
                        "text": cleaned,
                    })

    except Exception as exc:
        warnings.append(f"Failed to read {pdf_path.name}: {exc}")

write_jsonl(DATA_DIR / "raw_pages.jsonl", raw_pages)
write_jsonl(DATA_DIR / "clean_pages.jsonl", clean_pages)

# Build chunks across consecutive pages while retaining page provenance.
passages = []

for source_id in sorted(processed_sources):
    pages = [
        p for p in clean_pages if p["source_id"] == source_id
    ]
    pages.sort(key=lambda p: p["page"])

    words = []
    for page in pages:
        page_words = page["text"].split()
        for word in page_words:
            words.append((word, page["page"]))

    chunk_size = 400
    overlap = 50
    step = chunk_size - overlap
    chunk_number = 1

    for start in range(0, len(words), step):
        chunk = words[start:start + chunk_size]

        if len(chunk) < 80:
            continue

        chunk_text = " ".join(word for word, _ in chunk)
        page_numbers = [page for _, page in chunk]

        passages.append({
            "passage_id": f"{source_id}-C{chunk_number:05d}",
            "source_id": source_id,
            "page_start": min(page_numbers),
            "page_end": max(page_numbers),
            "word_count": len(chunk),
            "text": chunk_text,
        })
        chunk_number += 1

        if start + chunk_size >= len(words):
            break

write_jsonl(DATA_DIR / "passages.jsonl", passages)

# Report what was actually extracted.
report = {
    "pdf_files_found": len(pdf_files),
    "sources_processed": len(processed_sources),
    "raw_pages": len(raw_pages),
    "nonempty_clean_pages": len(clean_pages),
    "passages_created": len(passages),
    "possible_scanned_or_low_text_pages": sum(
        "Possible scanned/low-text page" in w for w in warnings
    ),
    "warnings": warnings,
}

(DATA_DIR / "extraction_report.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\n========== EXTRACTION REPORT ==========")
print(json.dumps(report, indent=2, ensure_ascii=False))
print("\nCreated:")
print("  data/raw_pages.jsonl")
print("  data/clean_pages.jsonl")
print("  data/passages.jsonl")
print("  data/extraction_report.json")
