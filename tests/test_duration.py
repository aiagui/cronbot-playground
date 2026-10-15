import unittest

from duration import format_duration


class FormatDurationTests(unittest.TestCase):
    def test_seconds(self):
        self.assertEqual(format_duration(0), "0s")
        self.assertEqual(format_duration(42), "42s")

    def test_minutes_and_seconds(self):
        self.assertEqual(format_duration(65), "1m 5s")
        self.assertEqual(format_duration(3599), "59m 59s")

    def test_hours_minutes_and_seconds(self):
        self.assertEqual(format_duration(3661), "1h 1m 1s")
        self.assertEqual(format_duration(7324), "2h 2m 4s")

    def test_negative_seconds(self):
        with self.assertRaisesRegex(ValueError, "seconds must not be negative"):
            format_duration(-1)

    def test_non_integer_seconds(self):
        for value in (1.5, "60", True, None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "seconds must be an integer"):
                    format_duration(value)


if __name__ == "__main__":
    unittest.main()
