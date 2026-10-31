import tempfile
import unittest
from pathlib import Path

from assistant_core import AssistantCore, safe_calculate
from database import ChatDatabase
from text_tools import analyze_text, clean_text, summarize_text


class TextToolsTests(unittest.TestCase):
    def test_clean_text(self):
        self.assertEqual(clean_text("سلام   دنیا  !\n  خوب"), "سلام دنیا! \nخوب".replace("! \n", "!\n"))

    def test_analyze_counts_words(self):
        result = analyze_text("سلام دنیا. این یک آزمایش است!")
        self.assertEqual(result["words"], 6)
        self.assertEqual(result["sentences"], 2)
        self.assertGreaterEqual(result["reading_minutes"], 1)

    def test_empty_summary(self):
        self.assertIn("وجود ندارد", summarize_text("  "))

    def test_summary_preserves_original_sentences(self):
        text = "گربه روی صندلی نشست. هوا امروز آفتابی است. گربه بعداً خوابید. من کتاب خواندم."
        summary = summarize_text(text, 2)
        self.assertEqual(len(summary.splitlines()), 2)
        for sentence in summary.splitlines():
            self.assertIn(sentence, text)


class CalculatorTests(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(safe_calculate("12*(4+3)"), 84)
        self.assertEqual(safe_calculate("-5 + 2"), -3)

    def test_rejects_code(self):
        with self.assertRaises(ValueError):
            safe_calculate("__import__('os').system('echo bad')")

    def test_division_by_zero(self):
        with self.assertRaises(ValueError):
            safe_calculate("10/0")


class AssistantTests(unittest.TestCase):
    def test_greeting(self):
        self.assertIn("سلام", AssistantCore().reply("سلام"))

    def test_calculation_command(self):
        self.assertIn("84", AssistantCore().reply("حساب کن: 12*(4+3)"))


class DatabaseTests(unittest.TestCase):
    def test_session_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            db = ChatDatabase(Path(temp) / "test.sqlite3")
            try:
                session = db.create_session()
                db.add_message(session, "user", "سلام")
                db.add_message(session, "assistant", "درود")
                messages = db.get_messages(session)
                self.assertEqual([m[0] for m in messages], ["user", "assistant"])
                self.assertEqual(messages[0][1], "سلام")
                self.assertEqual(db.list_sessions()[0][1], "سلام")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
