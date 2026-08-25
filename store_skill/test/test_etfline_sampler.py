import unittest
from datetime import datetime, timezone

from web.etfline_sampler import is_trading_time, seconds_to_next_sample


class EtflineSamplerTest(unittest.TestCase):
    def test_naive_datetime_is_treated_as_shanghai_time(self):
        self.assertTrue(is_trading_time(datetime(2026, 8, 18, 9, 30)))
        self.assertTrue(is_trading_time(datetime(2026, 8, 18, 15, 0)))
        self.assertFalse(is_trading_time(datetime(2026, 8, 18, 11, 31)))
        self.assertFalse(is_trading_time(datetime(2026, 8, 18, 15, 1)))

    def test_aware_datetime_is_converted_to_shanghai_time(self):
        self.assertTrue(is_trading_time(datetime(2026, 8, 18, 1, 30, tzinfo=timezone.utc)))
        self.assertFalse(is_trading_time(datetime(2026, 8, 18, 3, 31, tzinfo=timezone.utc)))

    def test_weekend_is_not_trading_time(self):
        self.assertFalse(is_trading_time(datetime(2026, 8, 22, 10, 0)))
        self.assertFalse(is_trading_time(datetime(2026, 8, 23, 14, 0)))

    def test_next_sample_aligns_to_five_minute_bucket(self):
        self.assertEqual(seconds_to_next_sample(datetime(2026, 8, 18, 9, 32)), 180)
        self.assertEqual(seconds_to_next_sample(datetime(2026, 8, 18, 9, 35)), 300)
        self.assertEqual(seconds_to_next_sample(datetime(2026, 8, 18, 11, 30)), 5400)

    def test_next_sample_skips_close_and_weekend(self):
        after_close = datetime(2026, 8, 21, 15, 1)
        monday_open = datetime(2026, 8, 24, 9, 30)
        self.assertEqual(seconds_to_next_sample(after_close), (monday_open - after_close).total_seconds())


if __name__ == "__main__":
    unittest.main()
