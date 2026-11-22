from voltcourt.audit import energy_charge, run_audit, load_tariff
from voltcourt.schema import Bill

SLABS = [{"upto": 100, "rate": 4}, {"upto": 300, "rate": 8}, {"upto": None, "rate": 12}]


def test_energy_charge_slabs():
    # 100*4 + 150*8 = 1600
    assert energy_charge(250, SLABS) == 1600.0


def test_correct_bill_has_no_findings():
    tariff = load_tariff()
    bill = Bill("123", 1000, 1250, 250, 30, 1600.0, 100.0, 272.0, 1972.0)
    assert run_audit(bill, tariff) == []


def test_catches_wrong_energy_charge():
    tariff = load_tariff()
    bill = Bill("123", 1000, 1250, 250, 30, 2000.0, 100.0, 336.0, 2436.0)
    rules = [f["rule"] for f in run_audit(bill, tariff)]
    assert "energy_charge_mismatch" in rules