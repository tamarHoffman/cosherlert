import pytest
from unittest.mock import MagicMock, patch
from cosherlert.poller import AlertEvent
from cosherlert.dispatcher import _process


def _make_alert(cat="10", oref_id="abc123", zones=None):
    return AlertEvent(
        oref_id=oref_id,
        cat=cat,
        title="test",
        zones=zones or ["בית שמש"],
    )


@patch("cosherlert.dispatcher.db")
def test_ignores_non_pre_warning_cat(mock_db):
    telephony = MagicMock()
    alert = _make_alert(cat="1")  # siren, not pre-warning
    _process(alert, telephony)
    telephony.send_tzintuq.assert_not_called()
    mock_db.already_dispatched.assert_not_called()


@patch("cosherlert.dispatcher.db")
def test_skips_already_dispatched(mock_db):
    mock_db.already_dispatched.return_value = True
    telephony = MagicMock()
    _process(_make_alert(), telephony)
    telephony.send_tzintuq.assert_not_called()


@patch("cosherlert.dispatcher.db")
def test_dispatches_to_subscribers(mock_db):
    mock_db.already_dispatched.return_value = False
    mock_db.get_subscribers_for_zones.return_value = ["0501234567", "0509876543"]
    telephony = MagicMock()
    telephony.send_tzintuq.return_value = True
    _process(_make_alert(), telephony)
    telephony.send_tzintuq.assert_called_once()
    phones_arg = telephony.send_tzintuq.call_args[0][0]
    assert "0501234567" in phones_arg
    mock_db.log_dispatch.assert_called_once()


@patch("cosherlert.dispatcher.db")
def test_no_dispatch_when_no_subscribers(mock_db):
    mock_db.already_dispatched.return_value = False
    mock_db.get_subscribers_for_zones.return_value = []
    telephony = MagicMock()
    _process(_make_alert(), telephony)
    telephony.send_tzintuq.assert_not_called()
    mock_db.log_dispatch.assert_called_once_with("abc123", "10", ["בית שמש"], 0)


@patch("cosherlert.dispatcher.db")
def test_dedup_prevents_double_dispatch(mock_db):
    mock_db.already_dispatched.side_effect = [False, True]
    mock_db.get_subscribers_for_zones.return_value = ["0501234567"]
    telephony = MagicMock()
    telephony.send_tzintuq.return_value = True
    alert = _make_alert()
    _process(alert, telephony)
    _process(alert, telephony)
    assert telephony.send_tzintuq.call_count == 1
