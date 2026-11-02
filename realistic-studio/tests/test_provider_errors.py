import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from provider_errors import rate_limit_message


class QuotaMessageTests(unittest.TestCase):
    def test_provider_wait_and_quota_headers_are_shown(self):
        exc=SimpleNamespace(response=SimpleNamespace(headers={'retry-after':'2.3','x-ratelimit-remaining-requests':'0','x-ratelimit-reset-requests':'2h3m','x-ratelimit-remaining-tokens':'100'}))
        message=rate_limit_message(exc)
        self.assertIn('3 seconds',message)
        self.assertIn('daily requests: 0; reset in 2h3m',message)
        self.assertIn('minute tokens: 100',message)
        self.assertIn('No automatic retry',message)

    def test_missing_headers_do_not_invent_wait_time(self):
        self.assertIn('Exact reset time was not provided',rate_limit_message(Exception('private response content')))
        self.assertNotIn('private response content',rate_limit_message(Exception('private response content')))

    def test_unexpected_header_values_are_not_exposed(self):
        exc=SimpleNamespace(response=SimpleNamespace(headers={'retry-after':'secret-value','x-ratelimit-remaining-requests':'0','x-ratelimit-reset-requests':'unexpected secret'}))
        self.assertNotIn('secret',rate_limit_message(exc))

if __name__=='__main__':unittest.main()
