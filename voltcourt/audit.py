import yaml


def load_tariff(path="config/tariff.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def energy_charge(units, slabs):
    total, lower = 0.0, 0
    for slab in slabs:
        upper = slab["upto"]
        if upper is None or units <= upper:
            total += (units - lower) * slab["rate"]
            return round(total, 2)
        total += (upper - lower) * slab["rate"]
        lower = upper
    return round(total, 2)


def run_audit(bill, tariff, tolerance=1.0):
    findings = []

    # Check 1: units = current - previous reading
    expected_units = bill.curr_reading - bill.prev_reading
    if abs(expected_units - bill.units_billed) > 0.5:
        findings.append({
            "rule": "units_mismatch",
            "expected": expected_units,
            "actual": bill.units_billed,
            "difference": bill.units_billed - expected_units,
            "severity": "high",
        })

    # Check 2: energy charge recomputed from slabs
    expected_energy = energy_charge(bill.units_billed, tariff["slabs"])
    if abs(expected_energy - bill.energy_charge) > tolerance:
        findings.append({
            "rule": "energy_charge_mismatch",
            "expected": expected_energy,
            "actual": bill.energy_charge,
            "difference": round(bill.energy_charge - expected_energy, 2),
            "severity": "high",
        })

    # Check 3: billing period too long
    if bill.billing_days > tariff["max_billing_days"]:
        findings.append({
            "rule": "billing_period_too_long",
            "expected": tariff["max_billing_days"],
            "actual": bill.billing_days,
            "difference": bill.billing_days - tariff["max_billing_days"],
            "severity": "medium",
        })

    # Check 4: duty recomputed
    expected_duty = round(
        (expected_energy + tariff["fixed_charge_per_month"])
        * tariff["duty_percent"] / 100, 2)
    if abs(expected_duty - bill.duty) > tolerance:
        findings.append({
            "rule": "duty_mismatch",
            "expected": expected_duty,
            "actual": bill.duty,
            "difference": round(bill.duty - expected_duty, 2),
            "severity": "medium",
        })

    return findings