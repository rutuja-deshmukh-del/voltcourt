"""Synthetic test tariff: numbers are made up for testing only and are NOT real MSEDCL rates."""
from voltcourt import engine

T = dict(provider_name="TestCo", category="Test-Res", effective_from="2024-01-01", effective_to=None,
         source_doc="synthetic", verified_on="2024-01-01", fixed_charge=100.0, fixed_prorate_days=0,
         wheeling_per_unit=1.0, fac_per_unit=0.5, duty_percent=10.0, duty_base="all", tax_percent=0.0,
         max_billing_days=35, slabs=[{"upto": 100, "rate": 4.0}, {"upto": 300, "rate": 8.0},
                                     {"upto": None, "rate": 12.0}])


def bill(**kw):
    # 250 units: energy 100*4 + 150*8 = 1600 ; fixed 100 ; wheeling 250 ; fac 125 ; base 2075 ; duty 207.5
    b = dict(consumer_no="1", prev=1000, curr=1250, multiplier=1, units=250, days=30, energy=1600,
             fixed=100, wheeling=250, fac=125, duty=207.5, tax=0, arrears=0, credits=0, total=2282.5,
             meter_status="Normal")
    b.update(kw)
    return b


def test_units():
    assert engine.units_consumed(1000, 1250, 2) == 500


def test_slabs():
    assert engine.slab_energy(250, T["slabs"])[0] == 1600
    assert engine.slab_energy(350, T["slabs"])[0] == 400 + 1600 + 600


def test_correct_bill_clear():
    r = engine.audit(bill(), T)
    assert r["status"] == "No Discrepancy Found" and r["overcharge"] == 0 and r["calc_total"] == 2282.5


def test_wrong_energy():
    r = engine.audit(bill(energy=2000, total=2682.5), T)
    assert r["status"] == "Potential Billing Discrepancy"
    assert r["overcharge"] > 0 and any(f["code"] == "energy_mismatch" for f in r["findings"])


def test_wrong_units():
    r = engine.audit(bill(units=300), T)
    assert any(f["code"] == "units_mismatch" for f in r["findings"])


def test_arithmetic_error_without_tariff():
    r = engine.audit(bill(total=2500), None)
    assert r["status"] == "Calculation Error" and r["overcharge"] == 217.5


def test_no_tariff_never_claims_clear_rates():
    r = engine.audit(bill(), None)
    assert r["status"] == "Tariff Verification Required" and r["calc_total"] is None


def test_missing_total():
    assert engine.audit(bill(total=0), T)["status"] == "Missing Information"


def test_reading_lower_manual_review():
    assert engine.audit(bill(prev=2000), T)["status"] in ("Manual Review Required", "Calculation Error",
                                                          "Potential Billing Discrepancy")


def test_estimated_meter():
    r = engine.audit(bill(meter_status="Estimated"), T)
    assert r["status"] == "Manual Review Required"


def test_long_period():
    r = engine.audit(bill(days=40), T)
    assert any(f["code"] == "days" for f in r["findings"])


def test_arrears_credits_reconcile():
    r = engine.audit(bill(arrears=100, credits=50, total=2332.5), T)
    assert r["status"] == "No Discrepancy Found"


def test_high_use_is_not_overcharge():
    r = engine.audit(bill(), T, history_avg=100)
    assert r["status"] == "No Discrepancy Found" and r["issue_count"] == 0


def test_wrong_energy_overcharge_is_independent():
    r = engine.audit(bill(energy=2000, total=2682.5), T)
    assert r["overcharge"] == 400.0 and [f["code"] for f in r["findings"]] == ["energy_mismatch"]