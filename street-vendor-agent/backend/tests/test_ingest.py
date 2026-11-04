import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import ingest


class IngestTests(unittest.TestCase):
    def test_prefers_ocr_sidecar_for_source_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory)
            source = raw_dir / "FAQHindi.pdf"
            ocr_copy = raw_dir / "FAQHindi.ocr.pdf"
            source.touch()
            ocr_copy.touch()

            with patch.object(ingest, "RAW_DIR", raw_dir):
                self.assertEqual(ingest._pdfs_to_process(), [(ocr_copy, "FAQHindi")])

    def test_empty_extraction_is_reported_and_not_written(self):
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory) / "raw"
            output_dir = Path(directory) / "processed"
            raw_dir.mkdir()
            (raw_dir / "FAQHindi.pdf").touch()
            output = io.StringIO()

            with (
                patch.object(ingest, "RAW_DIR", raw_dir),
                patch.object(ingest, "OUTPUT_DIR", output_dir),
                patch.object(ingest, "_make_converter", return_value=lambda _pdf: ""),
                contextlib.redirect_stdout(output),
                self.assertRaises(SystemExit) as error,
            ):
                ingest.main()

            self.assertEqual(error.exception.code, 1)
            self.assertIn("no extractable text", output.getvalue())
            self.assertFalse((output_dir / "FAQHindi.md").exists())


if __name__ == "__main__":
    unittest.main()
