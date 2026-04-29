import pytest
import json
import os
from unittest.mock import patch, mock_open
from app.orchestration.scan_memory import ScanMemory, MEMORY_FILE

def test_load_file_not_exists():
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = False
        sm = ScanMemory()
        assert sm.history == []
        mock_exists.assert_called_once_with(MEMORY_FILE)

def test_load_valid_json():
    test_data = [{"timestamp": "2023-01-01", "missions": []}]
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("builtins.open", mock_open(read_data=json.dumps(test_data))):
            sm = ScanMemory()
            assert sm.history == test_data

def test_load_invalid_json():
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("builtins.open", mock_open(read_data="invalid json")):
            sm = ScanMemory()
            assert sm.history == []

def test_load_exception_on_open():
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("builtins.open", side_effect=Exception("Permission denied")):
            sm = ScanMemory()
            assert sm.history == []
