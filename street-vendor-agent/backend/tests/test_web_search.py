import unittest
from unittest.mock import Mock, patch

from app import web_search


class OfficialWebsiteSearchTests(unittest.TestCase):
    @patch("app.web_search.requests.post")
    def test_search_filters_domains_and_returns_provenance_metadata(self, post):
        response = Mock(status_code=200)
        response.json.return_value = {
            "results": [
                {
                    "title": "PM SVANidhi",
                    "url": "https://pmsvanidhi.mohua.gov.in/scheme",
                    "raw_content": "Current scheme content",
                },
                {
                    "title": "Untrusted result",
                    "url": "https://example.com/scheme",
                    "content": "Do not include",
                },
            ]
        }
        post.return_value = response

        with patch.object(web_search, "TAVILY_API_KEY", "test-key"):
            result = web_search.search_official_sources("PM SVANidhi eligibility")

        self.assertIsNone(result["error"])
        self.assertEqual(len(result["results"]), 1)
        source = result["results"][0]
        self.assertEqual(source["content"], "Current scheme content")
        metadata = source["metadata"]
        self.assertEqual(metadata["source_type"], "official_web")
        self.assertEqual(metadata["source_url"], "https://pmsvanidhi.mohua.gov.in/scheme")
        self.assertEqual(metadata["document_title"], "PM SVANidhi")
        self.assertTrue(metadata["retrieval_date"].endswith("Z"))
        self.assertRegex(metadata["last_verified_date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(
            post.call_args.kwargs["json"]["include_domains"],
            list(web_search.OFFICIAL_DOMAINS),
        )

    @patch("app.web_search.requests.post")
    def test_missing_key_returns_error_without_requesting_search(self, post):
        with patch.object(web_search, "TAVILY_API_KEY", ""):
            result = web_search.search_official_sources("scheme")

        self.assertEqual(result["results"], [])
        self.assertIn("not configured", result["error"])
        post.assert_not_called()

    def test_rejects_non_https_and_lookalike_hosts(self):
        self.assertFalse(web_search._is_official_https_url("http://myscheme.gov.in/"))
        self.assertFalse(web_search._is_official_https_url("https://myscheme.gov.in.example.com/"))
        self.assertFalse(web_search._is_official_https_url("https://user@myscheme.gov.in/"))


if __name__ == "__main__":
    unittest.main()
