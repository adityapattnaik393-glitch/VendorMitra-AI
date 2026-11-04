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


def _pdfs_to_process() -> list[tuple[Path, str]]:
    files = sorted(RAW_DIR.glob("*.pdf"))
    inputs: list[tuple[Path, str]] = []
    for pdf in files:
        if pdf.name.endswith(".ocr.pdf"):
            continue
        ocr_copy = pdf.with_name(f"{pdf.stem}.ocr.pdf")
        inputs.append((ocr_copy if ocr_copy.exists() else pdf, pdf.stem))

    for pdf in files:
        if not pdf.name.endswith(".ocr.pdf"):
            continue
        original = pdf.with_name(f"{pdf.name.removesuffix('.ocr.pdf')}.pdf")
        if not original.exists():
            inputs.append((pdf, pdf.name.removesuffix(".ocr.pdf")))
    return inputs


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_inputs = _pdfs_to_process()
    if not pdf_inputs:
        raise SystemExit(f"No PDFs found in {RAW_DIR}")

    convert = _make_converter()
    processed = 0
    skipped: list[str] = []
    failed: list[str] = []
    for pdf, output_stem in pdf_inputs:
        try:
            markdown = convert(pdf)
        except Exception as error:
            print(f"FAILED: {pdf.name} -> {error}")
            failed.append(pdf.name)
            continue
        if not markdown.strip():
            print(
                f"SKIPPED: {pdf.name} produced no extractable text. "
                f"It may be scanned; add a searchable OCR copy named "
                f"'{output_stem}.ocr.pdf' and run ingestion again."
            )
            skipped.append(pdf.name)
            continue
        (OUTPUT_DIR / f"{output_stem}.md").write_text(markdown, encoding="utf-8")
        print("Processed:", pdf.name)
        processed += 1

    print(
        f"Ingestion summary: {processed} processed, {len(skipped)} without text, "
        f"{len(failed)} failed."
    )
    if skipped or failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
