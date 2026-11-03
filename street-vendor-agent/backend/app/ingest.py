from pathlib import Path
from docling.document_converter import DocumentConverter

_BACKEND_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = _BACKEND_DIR / "data" / "raw"
OUTPUT_DIR = _BACKEND_DIR / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

converter = DocumentConverter()

for pdf in RAW_DIR.glob("*.pdf"):

    result = converter.convert(str(pdf))

    markdown = result.document.export_to_markdown()

    output_file = OUTPUT_DIR / f"{pdf.stem}.md"

    output_file.write_text(
        markdown,
        encoding="utf-8"
    )

    print("Processed:", pdf.name)
