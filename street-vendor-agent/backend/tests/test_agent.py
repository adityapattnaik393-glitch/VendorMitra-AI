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
            ["Stored document — PM SVANidhi.md — data as of 2024-01-30"],
        )


class LiveGovernmentRetrievalTests(unittest.TestCase):
    @patch("app.agent.search_official_sources")
    @patch("app.agent.needs_live_search", return_value=True)
    @patch("app.agent.generate_answer", return_value="Scheme answer")
    @patch("app.agent.retrieve_context")
    def test_combines_pdf_and_live_context_with_clickable_source_metadata(
        self, retrieve, generate, _decision, search
    ):
        retrieve.return_value = [
            {
                "source": "Scheme Guidelines.md",
                "source_date": "2024-01-30",
                "content": "Stored eligibility guidance",
            }
        ]
        online_metadata = {
            "source_type": "official_web",
            "source_url": "https://myscheme.gov.in/schemes/example",
            "document_title": "Official scheme page",
            "retrieval_date": "2026-11-05T05:00:00Z",
            "last_verified_date": "2026-11-05",
        }
        search.return_value = {
            "results": [{"content": "Live eligibility guidance", "metadata": online_metadata}],
            "error": None,
        }

        result = ask_vendor_mitra("What is the current scheme eligibility?")

        context = generate.call_args.kwargs["context"]
        self.assertIn("[STORED PDF INFORMATION]", context)
        self.assertIn("Stored eligibility guidance", context)
        self.assertIn("[NEWLY RETRIEVED OFFICIAL WEBSITE INFORMATION]", context)
        self.assertIn("Live eligibility guidance", context)
        self.assertEqual(
            result["sources"][0],
            "Stored document — Scheme Guidelines.md — 2024-01-30",
        )
        self.assertEqual(result["sources"][1]["url"], online_metadata["source_url"])
        self.assertEqual(
            result["sources"][1]["retrieval_date"],
            online_metadata["retrieval_date"],
        )
        self.assertEqual(
            result["sources"][1]["last_verified_date"],
            online_metadata["last_verified_date"],
        )

    @patch("app.agent.search_official_sources")
    @patch("app.agent.needs_live_search", return_value=True)
    @patch("app.agent.generate_answer", return_value="Stored answer")
    @patch("app.agent.retrieve_context")
    def test_search_failure_falls_back_to_pdfs_and_discloses_verification_gap(
        self, retrieve, generate, _decision, search
    ):
        retrieve.return_value = [
            {
                "source": "Scheme Guidelines.md",
                "source_date": None,
                "content": "Stored eligibility guidance",
            }
        ]
        search.return_value = {"results": [], "error": "Official website search failed."}

        result = ask_vendor_mitra("What is the current scheme eligibility?")

        self.assertIn("Stored eligibility guidance", generate.call_args.kwargs["context"])
        self.assertIn("[ONLINE VERIFICATION STATUS]", generate.call_args.kwargs["context"])
        self.assertIn("couldn't verify", result["answer"])
        self.assertEqual(result["sources"], ["Stored document — Scheme Guidelines.md"])

    @patch("app.agent.search_official_sources")
    @patch("app.agent.needs_live_search", return_value=False)
    @patch("app.agent.generate_answer", return_value="General answer")
    @patch("app.agent.retrieve_context", return_value=[])
    def test_granite_can_decide_live_search_is_not_needed(
        self, _retrieve, _generate, _decision, search
    ):
        ask_vendor_mitra("What is a government scheme?")

        search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
