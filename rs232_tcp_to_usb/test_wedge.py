import unittest
import os
import tempfile
import csv
from unittest.mock import MagicMock, patch
from rs232_tcp_to_usb.main import (
    format_received_data,
    parse_and_simulate,
    simulate_keyboard_chars,
    log_to_txt,
    log_to_csv,
    log_to_xlsx
)

class TestKeyboardWedgeLogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_format_received_data_no_special(self):
        # Raw printing should return string as is when show_special is False
        self.assertEqual(format_received_data("Hello\r\nWorld\t", False), "Hello\r\nWorld\t")

    def test_format_received_data_with_special(self):
        # Special characters should be formatted into readable tags
        result = format_received_data("Hello\r\nWorld\t\x02", True)
        self.assertEqual(result, "Hello[CR][LF]World[TAB][STX]")

    @patch('rs232_tcp_to_usb.main.trigger_key')
    @patch('rs232_tcp_to_usb.main.trigger_text')
    def test_parse_and_simulate_basic(self, mock_trigger_text, mock_trigger_key):
        # Test basic characters simulation
        parse_and_simulate("ABC")
        mock_trigger_text.assert_any_call("ABC")

    @patch('rs232_tcp_to_usb.main.trigger_key')
    @patch('rs232_tcp_to_usb.main.trigger_text')
    def test_parse_and_simulate_escapes_and_tags(self, mock_trigger_text, mock_trigger_key):
        # Test bracket tags [ENTER] and escape sequence \t
        parse_and_simulate("A\\tB[ENTER]")
        mock_trigger_text.assert_any_call("A")
        mock_trigger_key.assert_any_call("tab")
        mock_trigger_text.assert_any_call("B")
        mock_trigger_key.assert_any_call("enter")

    @patch('rs232_tcp_to_usb.main.trigger_key')
    @patch('rs232_tcp_to_usb.main.trigger_text')
    def test_crlf_normalization(self, mock_trigger_text, mock_trigger_key):
        # When a CRLF sequence (\r\n) is received, we should trigger "enter" only once!
        simulate_keyboard_chars("Hello\r\nWorld")
        # trigger_key with "enter" should be called exactly once
        enter_calls = [call for call in mock_trigger_key.call_args_list if call[0][0] == 'enter']
        self.assertEqual(len(enter_calls), 1)

    def test_log_to_txt(self):
        # Verify that logging to text file creates the file and appends content
        filepath = os.path.join(self.test_dir.name, "log.txt")
        log_to_txt(filepath, "Test Raw Data 123")
        self.assertTrue(os.path.exists(filepath))
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Test Raw Data 123", content)

    def test_log_to_csv(self):
        # Verify that logging to CSV file creates headers and appends rows
        filepath = os.path.join(self.test_dir.name, "log.csv")
        log_to_csv(filepath, "Payload ABC")
        self.assertTrue(os.path.exists(filepath))
        with open(filepath, "r", newline="", encoding="utf-8") as f:
            reader = list(csv.reader(f))
        self.assertEqual(len(reader), 2)  # Headers row + 1 data row
        self.assertEqual(reader[0], ["Timestamp", "Received Data"])
        self.assertEqual(reader[1][1], "Payload ABC")

if __name__ == '__main__':
    unittest.main()
