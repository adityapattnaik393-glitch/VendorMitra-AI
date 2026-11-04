import unittest
from unittest.mock import patch

from app.agent import ask_vendor_mitra


class ResponseLanguageTests(unittest.TestCase):
    @patch("app.agent.generate_answer", return_value="उत्तर")
    @patch("app.agent.retrieve_context", return_value=[])
    def test_hindi_question_overrides_english_selection(self, _retrieve, generate):
        ask_vendor_mitra(
            "मुझे UPI कैसे सेट करना चाहिए?",
            preferred_language="English",
        )

        self.assertEqual(generate.call_args.kwargs["preferred_language"], "Hindi")

    @patch("app.agent.generate_answer", return_value="Answer")
    @patch("app.agent.retrieve_context", return_value=[])
    def test_selected_language_is_used_for_english_question(self, _retrieve, generate):
        ask_vendor_mitra(
            "How can I set up UPI?",
            preferred_language="Hindi",
        )

        self.assertEqual(generate.call_args.kwargs["preferred_language"], "Hindi")


if __name__ == "__main__":
    unittest.main()
