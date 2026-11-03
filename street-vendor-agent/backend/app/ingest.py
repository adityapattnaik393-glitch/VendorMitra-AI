"""Convert PDFs to Markdown using Docling or the lighter pypdf fallback."""
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = _BACKEND_DIR / "data" / "raw"
OUTPUT_DIR = _BACKEND_DIR / "data" / "processed"

def _make_converter():
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        print("Using Docling for PDF extraction")
        return lambda pdf: converter.convert(str(pdf)).document.export_to_markdown()
    except ImportError:
        from pypdf import PdfReader

        print("Docling not installed; using pypdf fallback")

        def convert(pdf: Path) -> str:
            reader = PdfReader(str(pdf))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)

        return convert


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {RAW_DIR}")

    convert = _make_converter()
    for pdf in pdfs:
        try:
            markdown = convert(pdf)
        except Exception as error:
            print(f"FAILED: {pdf.name} -> {error}")
            continue
        (OUTPUT_DIR / f"{pdf.stem}.md").write_text(markdown, encoding="utf-8")
        print("Processed:", pdf.name)


if __name__ == "__main__":
    main()
