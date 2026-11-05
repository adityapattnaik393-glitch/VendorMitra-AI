import unittest
from unittest.mock import Mock, patch

from app.granite import generate_answer, needs_live_search


class GraniteRequestTests(unittest.TestCase):
    @patch("app.granite.get_iam_token", return_value="test-token")
    @patch("app.granite.requests.post")
    def test_language_instruction_and_bearer_token_are_sent(self, post, _token):
        response = Mock(status_code=200)
        response.json.return_value = {
            "choices": [{"message": {"content": "नमस्ते"}}]
        }
        post.return_value = response

        answer = generate_answer(
            question="How do I accept UPI?",
            context="Verified source",
            preferred_language="Hindi",
        )

        self.assertEqual(answer, "नमस्ते")
        request = post.call_args.kwargs
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-token")
        self.assertIn("entire answer in Hindi", request["json"]["messages"][0]["content"])

    @patch("app.granite.get_iam_token", side_effect=["expired-token", "fresh-token"])
    @patch("app.granite.requests.post")
    def test_unauthorized_request_retries_with_refreshed_token(self, post, _token):
        unauthorized = Mock(status_code=401)
        success = Mock(status_code=200)
        success.json.return_value = {
            "choices": [{"message": {"content": "Ready"}}]
        }
        post.side_effect = [unauthorized, success]

        self.assertEqual(
            generate_answer(question="Hello", context="(none)"),
            "Ready",
        )
        self.assertEqual(post.call_count, 2)
        self.assertEqual(
            post.call_args_list[1].kwargs["headers"]["Authorization"],
            "Bearer fresh-token",
        )


    @patch("app.granite._request_chat", return_value='{"needs_live_search": false}')
    def test_granite_classifies_stored_scheme_information(self, request):
        self.assertFalse(needs_live_search("What is this scheme?", "PDF details"))
        self.assertIn(
            "government-scheme question",
            request.call_args.args[0][0]["content"],
        )

    @patch("app.granite._request_chat", return_value="not valid JSON")
    def test_unclear_classification_defaults_to_live_verification(self, _request):
        self.assertTrue(needs_live_search("What are current rules?", "PDF details"))


if __name__ == "__main__":
    unittest.main()
