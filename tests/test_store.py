import os
import pytest
from voltcourt import auth, store, engine
from tests.test_engine import T, bill


@pytest.fixture(autouse=True)
def tmpdb(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB", str(tmp_path / "t.db"))


def test_register_login():
    ok, _, code = auth.register("Test User", "t@gmail.com", "Volt@2026")
    assert ok and auth.login("t@gmail.com", "Volt@2026") == "Test User"
    assert auth.login("t@gmail.com", "bad") is None


def test_providers_seeded_without_tariffs():
    assert any("MSEDCL" in p["name"] for p in store.providers()) and store.list_tariffs() == []


def test_tariff_lookup_only_verified_and_dated():
    pid = store.providers()[0]["id"]
    t = dict(provider_id=pid, category="C", effective_from="2024-01-01", effective_to="2024-12-31",
             slabs=T["slabs"], fixed_charge=1, wheeling_per_unit=0, fac_per_unit=0, duty_percent=0,
             duty_base="all", tax_percent=0, source_doc="s", verified_on="2024-01-01", verified=False)
    store.add_tariff(t, "a@gmail.com")
    assert store.find_tariff(pid, "C", "2024-06-01") is None
    store.set_tariff_verified(store.list_tariffs()[0]["id"], True, "2024-02-01")
    assert store.find_tariff(pid, "C", "2024-06-01") is not None
    assert store.find_tariff(pid, "C", "2025-06-01") is None


def test_audit_isolation():
    res = engine.audit(bill(), T)
    aid = store.save_audit("a@gmail.com", dict(bill(), bill_date="2024-06-01"), res, 1)
    assert store.get_audit("a@gmail.com", aid) is not None
    assert store.get_audit("b@gmail.com", aid) is None
    assert store.list_audits("b@gmail.com") == []