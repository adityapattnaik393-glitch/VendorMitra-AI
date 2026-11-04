import unittest
from unittest.mock import patch

from app.agent import _extract_vendor_profile, _infer_task, ask_vendor_mitra


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


class VendorProfileGenerationTests(unittest.TestCase):
    def test_extracts_products_and_location_from_first_message(self):
        profile = _extract_vendor_profile(
            "I sell fruit in Pune's Camp area.",
            None,
        )

        self.assertEqual(profile["products"], ["fruit"])
        self.assertEqual(profile["business_type"], "Fruit seller")
        self.assertEqual(profile["location"], "Pune Camp")

    def test_preserves_saved_profile_when_extracting_message(self):
        profile = _extract_vendor_profile(
            "I sell fruit in Pune Camp.",
            {"location": "Mumbai", "products": ["Tea"]},
        )

        self.assertEqual(profile["location"], "Mumbai")
        self.assertEqual(profile["products"], ["Tea"])

    def test_detects_business_profile_and_promotion_requests(self):
        self.assertEqual(
            _infer_task("Make me a business profile for my stall", "general"),
            "business_profile",
        )
        self.assertEqual(
            _infer_task("Write a WhatsApp promotion for my shop", "general"),
            "promotional_materials",
        )
        self.assertEqual(
            _infer_task("मेरी दुकान की प्रोफ़ाइल बनाएं", "general"),
            "business_profile",
        )
        self.assertEqual(
            _infer_task("मेरे स्टॉल का प्रचार पोस्टर बनाएं", "general"),
            "promotional_materials",
        )

    def test_extracts_hindi_products_and_location(self):
        profile = _extract_vendor_profile("मैं पुणे के कैंप इलाके में फल बेचता हूँ।", None)

        self.assertEqual(profile["products"], ["फल"])
        self.assertEqual(profile["business_type"], "फल विक्रेता")
        self.assertEqual(profile["location"], "पुणे के कैंप इलाके")

    @patch("app.agent.generate_answer", return_value="Vendor profile")
    @patch("app.agent.retrieve_context", return_value=[])
    def test_business_profile_is_generated_without_pdf_sources(self, _retrieve, generate):
        result = ask_vendor_mitra(
            "Create a business profile for me",
            vendor_profile={
                "business_type": "Fruit seller",
                "products": ["Mangoes"],
                "location": "Pune Camp",
            },
        )

        self.assertEqual(result["answer"], "Vendor profile")
        self.assertEqual(generate.call_args.kwargs["task"], "business_profile")
        self.assertIn("Pune Camp", generate.call_args.kwargs["vendor_context"])

    @patch("app.agent.generate_answer", return_value="Scheme answer")
    @patch(
        "app.agent.retrieve_context",
        return_value=[
            {
                "source": "PM SVANidhi.md",
                "source_date": "data as of 2024-01-30",
                "content": "Historical aggregate data",
            }
        ],
    )
    def test_dated_source_is_in_prompt_and_label_does_not_repeat_as_of(
        self, _retrieve, generate
    ):
        result = ask_vendor_mitra("What does the source report?")

        self.assertIn(
            "Source date: data as of 2024-01-30",
            generate.call_args.kwargs["context"],
        )
        self.assertEqual(
            result["sources"],
            ["PM SVANidhi.md — data as of 2024-01-30"],
        )


if __name__ == "__main__":
    unittest.main()
