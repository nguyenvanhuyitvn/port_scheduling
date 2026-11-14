"""Streamlit AppTest exercises actual widget dispatch and a saved scheduling run."""

import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def test_navigation_and_single_scheduling(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        self.assertEqual(len(at.exception), 0)
        # Data validation and persistence of session input.
        next(
            b for b in at.button if b.label == "Kiểm tra và dùng dữ liệu này"
        ).click().run()
        self.assertEqual(len(at.exception), 0)
        menu = at.sidebar.radio[0]
        choices = list(menu.options)
        for name in choices[1:]:
            at.sidebar.radio[0].set_value(name).run()
            self.assertEqual(len(at.exception), 0, name)
        at.sidebar.radio[0].set_value(choices[1]).run()
        # Run a real construction: charts + CSV/JSON + download serialization.
        at.multiselect[0].set_value(["greedy"])
        next(b for b in at.button if b.label == "Chạy lập lịch").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertGreater(len(at.metric), 0)


if __name__ == "__main__":
    unittest.main()
