# -*- coding: utf-8 -*-
"""Tests for opensquat.api_client."""
from unittest import TestCase
from unittest.mock import MagicMock

import requests

from opensquat.api_client import (
    APIClient,
    APIAuthError,
    APIBadRequest,
    APIError,
    APIPlanError,
    APIQuotaExhausted,
    LookalikeResult,
)


def _mock_response(status_code, json_body=None, raise_on_json=False):
    response = MagicMock()
    response.status_code = status_code
    if raise_on_json:
        response.json.side_effect = ValueError("not json")
    else:
        response.json.return_value = json_body or {}
    return response


SAMPLE_OK_BODY = {
    "keyword": "paypal",
    "count": 4,
    "total": 48,
    "balance": 199,
    "history_days": 7,
    "max_results": 50,
    "query_time": 0.142,
    "results": [
        {"domain": "paypal-verify.com", "tld": "com", "date": "29-03-2026"},
        {"domain": "paypal-login-secure.net", "tld": "net", "date": "29-03-2026"},
        {
            "domain": "xn--pypal-4ve.com",
            "tld": "com",
            "date": "29-03-2026",
            "idn": True,
            "unicode_domain": "p\u0430ypal.com",
        },
        {"domain": "my-paypal-support.org", "tld": "org", "date": "28-03-2026"},
    ],
}


class TestAPIClientInit(TestCase):

    def test_requires_api_key(self):
        with self.assertRaises(ValueError):
            APIClient(api_key="")
        with self.assertRaises(ValueError):
            APIClient(api_key=None)

    def test_sets_session_headers(self):
        session = MagicMock()
        session.headers = {}
        APIClient(api_key="os_test_key", session=session)
        self.assertEqual("os_test_key", session.headers["x-api-key"])
        self.assertTrue(session.headers["User-Agent"].startswith("openSquat-"))
        self.assertEqual("application/json", session.headers["Accept"])

    def test_strips_trailing_slash_from_base_url(self):
        client = APIClient(
            api_key="k", base_url="https://example.com/", session=MagicMock(headers={})
        )
        self.assertEqual("https://example.com", client.base_url)

    def test_context_manager_closes_session(self):
        session = MagicMock(headers={})
        with APIClient(api_key="k", session=session) as _:
            pass
        session.close.assert_called_once()


class TestLookalikeHappyPath(TestCase):

    def setUp(self):
        self.session = MagicMock(headers={})
        self.client = APIClient(api_key="os_test_key", session=self.session)

    def test_returns_punycode_domains(self):
        self.session.post.return_value = _mock_response(200, SAMPLE_OK_BODY)

        result = self.client.lookalike("paypal")

        self.assertIsInstance(result, LookalikeResult)
        self.assertEqual("paypal", result.keyword)
        self.assertEqual(
            [
                "paypal-verify.com",
                "paypal-login-secure.net",
                "xn--pypal-4ve.com",
                "my-paypal-support.org",
            ],
            result.domains,
        )
        self.assertEqual(199, result.balance)
        self.assertEqual(4, result.count)
        self.assertEqual(48, result.total)
        self.assertEqual(0.142, result.query_time)

    def test_idn_domain_returned_as_punycode(self):
        self.session.post.return_value = _mock_response(200, SAMPLE_OK_BODY)
        result = self.client.lookalike("paypal")
        self.assertIn("xn--pypal-4ve.com", result.domains)
        self.assertNotIn("p\u0430ypal.com", result.domains)

    def test_url_encodes_keyword(self):
        self.session.post.return_value = _mock_response(200, SAMPLE_OK_BODY)
        self.client.lookalike("hello world")
        called_url = self.session.post.call_args[0][0]
        self.assertIn("hello%20world", called_url)

    def test_url_encodes_unicode_keyword(self):
        self.session.post.return_value = _mock_response(200, SAMPLE_OK_BODY)
        self.client.lookalike("p\u00e4ypal")
        called_url = self.session.post.call_args[0][0]
        self.assertIn("p%C3%A4ypal", called_url)

    def test_optional_params_omitted_when_none(self):
        self.session.post.return_value = _mock_response(200, SAMPLE_OK_BODY)
        self.client.lookalike("paypal")
        params = self.session.post.call_args[1]["params"]
        self.assertEqual({"format": "json"}, params)

    def test_optional_params_included_when_set(self):
        self.session.post.return_value = _mock_response(200, SAMPLE_OK_BODY)
        self.client.lookalike(
            "paypal", fuzziness="auto", history_days=7, max_results=50
        )
        params = self.session.post.call_args[1]["params"]
        self.assertEqual("json", params["format"])
        self.assertEqual("auto", params["fuzziness"])
        self.assertEqual(7, params["history_days"])
        self.assertEqual(50, params["max_results"])

    def test_empty_results_returns_empty_list(self):
        body = dict(SAMPLE_OK_BODY)
        body["results"] = []
        body["count"] = 0
        self.session.post.return_value = _mock_response(200, body)
        result = self.client.lookalike("nothing")
        self.assertEqual([], result.domains)


class TestLookalikeErrors(TestCase):

    def setUp(self):
        self.session = MagicMock(headers={})
        self.client = APIClient(api_key="os_test_key", session=self.session)

    def test_400_raises_bad_request(self):
        self.session.post.return_value = _mock_response(
            400, {"detail": "Keyword must be 2-64 characters"}
        )
        with self.assertRaises(APIBadRequest) as ctx:
            self.client.lookalike("a")
        self.assertIn("Keyword", str(ctx.exception))

    def test_401_raises_auth_error(self):
        self.session.post.return_value = _mock_response(
            401, {"detail": "Invalid or inactive API key"}
        )
        with self.assertRaises(APIAuthError):
            self.client.lookalike("paypal")

    def test_403_raises_plan_error(self):
        self.session.post.return_value = _mock_response(
            403, {"detail": "Your plan allows max 7 days history"}
        )
        with self.assertRaises(APIPlanError) as ctx:
            self.client.lookalike("paypal")
        self.assertIn("plan", str(ctx.exception).lower())

    def test_429_raises_quota_with_balance(self):
        self.session.post.return_value = _mock_response(
            429,
            {
                "detail": "Quota exceeded. Please upgrade your plan or wait for quota reset.",
                "balance": 0,
            },
        )
        with self.assertRaises(APIQuotaExhausted) as ctx:
            self.client.lookalike("paypal")
        self.assertEqual(0, ctx.exception.balance)

    def test_500_raises_generic_api_error(self):
        self.session.post.return_value = _mock_response(500, {"detail": "internal"})
        with self.assertRaises(APIError) as ctx:
            self.client.lookalike("paypal")
        # Make sure it's NOT one of the typed subclasses
        self.assertNotIsInstance(ctx.exception, APIAuthError)
        self.assertNotIsInstance(ctx.exception, APIPlanError)
        self.assertNotIsInstance(ctx.exception, APIQuotaExhausted)
        self.assertNotIsInstance(ctx.exception, APIBadRequest)

    def test_network_error_wrapped_in_api_error(self):
        self.session.post.side_effect = requests.exceptions.ConnectionError("boom")
        with self.assertRaises(APIError) as ctx:
            self.client.lookalike("paypal")
        self.assertIn("Network error", str(ctx.exception))

    def test_invalid_json_in_200_response_raises(self):
        self.session.post.return_value = _mock_response(200, raise_on_json=True)
        with self.assertRaises(APIError) as ctx:
            self.client.lookalike("paypal")
        self.assertIn("parse JSON", str(ctx.exception))

    def test_empty_keyword_raises(self):
        with self.assertRaises(APIBadRequest):
            self.client.lookalike("")
