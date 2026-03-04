import pytest
import os
import tempfile
from cosherlert import db, config


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(config, "DB_PATH", db_file)
    db.init_db()
    yield


def test_upsert_and_subscribe():
    db.add_subscription("0501234567", "בית שמש")
    phones = db.get_subscribers_for_zones(["בית שמש"])
    assert "0501234567" in phones


def test_multi_zone_subscription():
    db.add_subscription("0501234567", "בית שמש")
    db.add_subscription("0501234567", "ירושלים")
    zones = db.get_subscriptions_for_phone("0501234567")
    assert "בית שמש" in zones
    assert "ירושלים" in zones


def test_subscriber_receives_any_matching_zone():
    db.add_subscription("0501234567", "בית שמש")
    db.add_subscription("0509999999", "ירושלים")
    phones = db.get_subscribers_for_zones(["בית שמש", "נתניה"])
    assert "0501234567" in phones
    assert "0509999999" not in phones
    


def test_unsubscribe_removes_all():
    db.add_subscription("0501234567", "בית שמש")
    db.add_subscription("0501234567", "ירושלים")
    db.remove_all_subscriptions("0501234567")
    phones = db.get_subscribers_for_zones(["בית שמש"])
    assert "0501234567" not in phones


def test_dedup_already_dispatched():
    db.log_dispatch("id-001", "10", ["בית שמש"], 3)
    assert db.already_dispatched("id-001") is True
    assert db.already_dispatched("id-999") is False


def test_duplicate_subscription_ignored():
    db.add_subscription("0501234567", "בית שמש")
    db.add_subscription("0501234567", "בית שמש")  # should not raise
    phones = db.get_subscribers_for_zones(["בית שמש"])
    assert phones.count("0501234567") == 1
