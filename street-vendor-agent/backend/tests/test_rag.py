import unittest
from unittest.mock import patch

from app import rag


class RetrievalSourceDateTests(unittest.TestCase):
    @patch("app.rag._model")
    @patch("app.rag._collection")
    def test_preserves_source_date_from_chunk_metadata(self, collection, model):
        collection.return_value.count.return_value = 1
        collection.return_value.query.return_value = {
            "documents": [["Historical official data"]],
            "metadatas": [[
                {
                    "source": "PM SVANidhi data.md",
                    "source_date": "data as of 2024-01-30",
                }
            ]],
        }
        model.return_value.encode.return_value.tolist.return_value = [[0.1, 0.2]]

        results = rag.retrieve_context("eligible applications")

        self.assertEqual(
            results[0]["source_date"],
            "data as of 2024-01-30",
        )


if __name__ == "__main__":
    unittest.main()
