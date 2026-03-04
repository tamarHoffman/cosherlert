"""
Tests for the Yemot IVR webhook routes.
Uses Flask test client — no real HTTP or telephony calls.
"""
import pytest
from cosherlert.ivr.routes import app
from cosherlert import db


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Each test gets a fresh DB file."""
    import cosherlert.config as _config
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(_config, "DB_PATH", db_file)
    db.init_db()
    yield


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


PHONE = "0501234567"


def _get(client, path, **params):
    params.setdefault("ApiPhone", PHONE)
    return client.get(path, query_string=params)


# ─── /ivr/start ──────────────────────────────────────────────────────────────

def test_start_new_user_shows_not_registered(client):
    rv = _get(client, "/ivr/start")
    assert rv.status_code == 200
    body = rv.data.decode("utf-8")
    assert "read=t-" in body
    assert "אינך רשום" in body
    assert "read_input=digit" in body


def test_start_registered_user_shows_zones(client):
    db.add_subscription(PHONE, "בית שמש")
    db.add_subscription(PHONE, "ירושלים")
    rv = _get(client, "/ivr/start")
    body = rv.data.decode("utf-8")
    assert "בית שמש" in body
    assert "ירושלים" in body


# ─── /ivr/menu ───────────────────────────────────────────────────────────────

def test_menu_digit_1_shows_zone_page(client):
    rv = _get(client, "/ivr/menu", digit="1")
    body = rv.data.decode("utf-8")
    assert "read=t-בחר אזור" in body
    assert "read_input=digit" in body


def test_menu_digit_2_unsubscribes(client):
    db.add_subscription(PHONE, "תל אביב")
    rv = _get(client, "/ivr/menu", digit="2")
    body = rv.data.decode("utf-8")
    assert "בוטל" in body
    assert "hangup=now" in body
    assert db.get_subscriptions_for_phone(PHONE) == []


def test_menu_invalid_digit_redirects(client):
    rv = _get(client, "/ivr/menu", digit="5")
    body = rv.data.decode("utf-8")
    assert "לא חוקית" in body or "goes=/ivr/start" in body


# ─── /ivr/zones ──────────────────────────────────────────────────────────────

def test_zones_first_page_lists_9_zones(client):
    rv = _get(client, "/ivr/zones", page="0")
    body = rv.data.decode("utf-8")
    # Should have exactly 9 read=t- lines for numbered zones (לחץ 1–9 עבור ...)
    zone_lines = [l for l in body.splitlines() if "עבור" in l and "read=t-" in l]
    assert len(zone_lines) == 9


def test_zones_second_page_accessible(client):
    rv = _get(client, "/ivr/zones", page="1")
    body = rv.data.decode("utf-8")
    assert "read=t-" in body
    assert "read_input=digit" in body


def test_zones_digit_selection_subscribes(client):
    # Press "1" on page 0 → subscribes to ZONE_LIST[0] = "בית שמש"
    rv = _get(client, "/ivr/zones", digit="1", prev_page="0", page="0")
    body = rv.data.decode("utf-8")
    assert "בית שמש" in body
    assert "נרשמת" in body
    subs = db.get_subscriptions_for_phone(PHONE)
    assert "בית שמש" in subs


def test_zones_digit_0_goes_to_next_page(client):
    # digit=0 should NOT subscribe anything, should show next page
    rv = _get(client, "/ivr/zones", digit="0", prev_page="0", page="1")
    body = rv.data.decode("utf-8")
    subs = db.get_subscriptions_for_phone(PHONE)
    assert subs == []  # nothing subscribed
    assert "read=t-" in body


# ─── /ivr/done ───────────────────────────────────────────────────────────────

def test_done_with_subscriptions(client):
    db.add_subscription(PHONE, "חיפה")
    rv = _get(client, "/ivr/done")
    body = rv.data.decode("utf-8")
    assert "חיפה" in body
    assert "hangup=now" in body


def test_done_without_subscriptions(client):
    rv = _get(client, "/ivr/done")
    body = rv.data.decode("utf-8")
    assert "hangup=now" in body
