import pytest
from unittest.mock import patch, MagicMock
from cosherlert.poller import _fetch_alert, AlertEvent


def _mock_response(json_data):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.text = str(json_data) if json_data else ""
    mock.json.return_value = json_data
    return mock


@patch("cosherlert.poller.requests.get")
def test_fetch_alert_returns_event(mock_get):
    mock_get.return_value = _mock_response({
        "id": "123456", "cat": "10",
        "title": "התרעה", "data": ["בית שמש", "ירושלים"], "desc": ""
    })
    alert = _fetch_alert()
    assert alert is not None
    assert alert.oref_id == "123456"
    assert alert.cat == "10"
    assert "בית שמש" in alert.zones


@patch("cosherlert.poller.requests.get")
def test_fetch_alert_empty_response_returns_none(mock_get):
    mock_get.return_value = _mock_response(None)
    alert = _fetch_alert()
    assert alert is None


@patch("cosherlert.poller.requests.get")
def test_fetch_alert_empty_dict_returns_none(mock_get):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.text = "{}"
    resp.json.return_value = {}
    mock_get.return_value = resp
    alert = _fetch_alert()
    assert alert is None


@patch("cosherlert.poller.requests.get")
def test_fetch_alert_network_error_returns_none(mock_get):
    mock_get.side_effect = Exception("network error")
    alert = _fetch_alert()
    assert alert is None
