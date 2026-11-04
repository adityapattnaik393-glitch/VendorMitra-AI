import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class ChatProfileTests(unittest.TestCase):
    def test_saved_vendor_details_are_passed_to_the_assistant(self):
        client = TestClient(app)
        with patch(
            "app.main.ask_vendor_mitra",
            return_value={"answer": "Here is advice for your fruit stall.", "sources": []},
        ) as ask:
            response = client.post(
                "/chat",
                json={
                    "question": "How can I grow my business?",
                    "response_language": "Hindi",
                    "vendor": {
                        "business_name": "Fresh Fruits",
                        "business_type": "Fruit seller",
                        "products": ["Mangoes", "Bananas"],
                        "location": "Pune Camp",
                    },
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ask.call_args.kwargs["vendor_profile"],
            {
                "business_name": "Fresh Fruits",
                "business_type": "Fruit seller",
                "products": ["Mangoes", "Bananas"],
                "location": "Pune Camp",
            },
        )
        self.assertEqual(ask.call_args.kwargs["preferred_language"], "Hindi")

    def test_promotional_materials_task_is_accepted(self):
        client = TestClient(app)
        with patch(
            "app.main.ask_vendor_mitra",
            return_value={"answer": "Ready-to-use promotion", "sources": []},
        ) as ask:
            response = client.post(
                "/chat",
                json={
                    "question": "Create a WhatsApp promotion for my stall.",
                    "task": "promotional_materials",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ask.call_args.kwargs["task"], "promotional_materials")


if __name__ == "__main__":
    unittest.main()
