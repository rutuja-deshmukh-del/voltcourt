"""Independent audit engine. Pure Python maths: no LLM, no network.

Tariff-dependent checks run ONLY when a verified tariff is supplied. Without one the engine
still checks meter units and bill arithmetic, and reports 'Tariff Verification Required'.
"""

TOL = 1.0  # rupees of rounding tolerance
STATUSES = ["No Discrepancy Found", "Missing Information", "Manual Review Required",
            "Tariff Verification Required", "Potential Billing Discrepancy", "Calculation Error"]
COMPONENTS = [("energy", "Energy charge"), ("fixed", "Fixed charge"), ("wheeling", "Wheeling charge"),
              ("fac", "Fuel adjustment charge"), ("duty", "Electricity duty"), ("tax", "Tax")]


def r2(x):
    return round(float(x) + 1e-9, 2)


def units_consumed(prev, curr, multiplier=1.0):
    return r2((float(curr) - float(prev)) * float(multiplier or 1))


def slab_energy(units, slabs):
    """slabs: [{'upto': 100, 'rate': r1}, {'upto': 300, 'rate': r2}, {'upto': None, 'rate': r3}]"""
    total, lower, parts = 0.0, 0.0, []
    for s in slabs:
        upto = s.get("upto")
        band = (units - lower) if upto is None else (min(units, upto) - lower)
        if band > 0:
            amt = band * float(s["rate"])
            parts.append({"from": lower, "to": min(units, upto) if upto is not None else units,
                          "units": r2(band), "rate": float(s["rate"]), "amount": r2(amt)})
            total += amt
        if upto is None or units <= upto:
            break
        lower = upto
    return r2(total), parts


def _f(code, status, title, found, expected, diff, how, rule, nxt,
       money=False, counts=True, info=False):
    return dict(code=code, status=status, title=title, found=found, expected=expected,
                difference=diff, how=how, rule=rule, next_step=nxt, money=money,
                counts=counts, info=info)


def tariff_reference(t):
    if not t:
        return "No verified tariff found for this provider, category and bill date."
    return (f"{t['provider_name']} | {t['category']} | effective {t['effective_from']} to "
            f"{t.get('effective_to') or 'open'} | source: {t['source_doc']} | verified {t['verified_on']}")


def audit(inp, tariff=None, history_avg=None):
    g = lambda k: float(inp.get(k) or 0)
    prev, curr, mult = g("prev"), g("curr"), g("multiplier") or 1.0
    units_billed, days, total = g("units"), int(g("days")), g("total")
    arrears, credits = g("arrears"), g("credits")
    meter = inp.get("meter_status", "Normal")
    billed = {k: g(k) for k, _ in COMPONENTS}
    F = []
    ref = tariff_reference(tariff)

    if total <= 0:
        F.append(_f("missing_total", "Missing Information", "Total bill amount is missing",
                    total, None, None, "A total above zero is needed to audit the bill.", "n/a",
                    "Enter the total payable amount from your bill.", counts=False))
        return _result(F, billed, None, None, total, None, ref, tariff, checks=[
            dict(name="Required data present", outcome="fail", detail="Total bill amount is missing")])

    units_calc = None
    if curr < prev:
        F.append(_f("reading_inconsistent", "Manual Review Required",
                    "Current reading is lower than the previous reading", curr, prev, None,
                    "Meter readings normally increase. This can be a typing error, a meter "
                    "replacement or a rollover.", "n/a",
                    "Check the readings on the bill. If the meter was replaced, ask the utility for "
                    "the final and initial readings.", counts=False))
    else:
        units_calc = units_consumed(prev, curr, mult)
        if abs(units_calc - units_billed) > 0.5:
            F.append(_f("units_mismatch", "Potential Billing Discrepancy",
                        "Units billed do not match the meter readings", units_billed, units_calc,
                        r2(units_billed - units_calc),
                        f"({curr:g} - {prev:g}) x multiplier {mult:g} = {units_calc:g} units",
                        "Units = (current - previous) x multiplier",
                        "Check the meter multiplier and readings on your bill, then ask the utility "
                        "to explain how the billed units were derived."))
    if meter in ("Estimated", "Faulty / locked"):
        F.append(_f("meter_status", "Manual Review Required", f"Meter status is '{meter}'",
                    meter, "Actual reading", None,
                    "The bill is based on an estimate or an unreadable meter, so charges cannot be "
                    "fully verified.", "n/a",
                    "Ask the utility for an actual meter reading and a revised bill if needed.",
                    counts=False))

    basis = units_calc if units_calc is not None else units_billed

    # arithmetic: tariff independent
    sum_billed = r2(sum(billed.values()) + arrears - credits)
    if abs(total - sum_billed) > TOL:
        F.append(_f("arithmetic", "Calculation Error", "Charges do not add up to the total",
                    total, sum_billed, r2(total - sum_billed),
                    "energy + fixed + wheeling + FAC + duty + tax + arrears - credits = "
                    f"{sum_billed:,.2f}", "Bill arithmetic",
                    "Ask the utility to explain the difference between the listed charges and the total.",
                    money=True))

    expected_comp = {}
    parts = []
    calc_total = None
    if tariff is None:
        F.append(_f("no_tariff", "Tariff Verification Required",
                    "No verified tariff available for this bill", "n/a", "Verified tariff", None,
                    "Rate checks were skipped. Only unit and arithmetic checks were done.",
                    ref, "Ask an administrator to add the verified tariff order for this provider, "
                    "category and period, then audit again.", counts=False))
    else:
        t = tariff
        e_amt, parts = slab_energy(basis, t["slabs"])
        fixed = t["fixed_charge"]
        if t.get("fixed_prorate_days"):
            fixed = fixed * days / t["fixed_prorate_days"]
        expected_comp["energy"] = e_amt
        expected_comp["fixed"] = r2(fixed)
        expected_comp["wheeling"] = r2(basis * t["wheeling_per_unit"])
        expected_comp["fac"] = r2(basis * t["fac_per_unit"])
        base = (sum(expected_comp[k] for k in ("energy", "fixed", "wheeling", "fac"))
                if t["duty_base"] == "all" else expected_comp["energy"])
        expected_comp["duty"] = r2(base * t["duty_percent"] / 100)
        expected_comp["tax"] = r2(base * t["tax_percent"] / 100)
        calc_total = r2(sum(expected_comp.values()) + arrears - credits)
        labels = dict(COMPONENTS)
        for k, exp in expected_comp.items():
            diff = r2(billed[k] - exp)
            if abs(diff) > TOL:
                unexpected = exp == 0 and billed[k] > 0
                how = (f"Slabs: " + "; ".join(f"{p['units']:g} units x {p['rate']:g} = {p['amount']:,.2f}"
                                              for p in parts) if k == "energy"
                       else f"Expected {exp:,.2f} from tariff using {basis:g} units"
                       + ("; duty/tax computed on the expected charges" if k in ("duty", "tax") else ""))
                F.append(_f(f"{k}_mismatch", "Potential Billing Discrepancy",
                            ("Unexpected charge: " if unexpected else "Incorrect ") + labels[k].lower(),
                            billed[k], exp, diff, how, ref,
                            "Ask the utility which tariff clause supports this amount and request a "
                            "corrected bill if it cannot be justified.", money=True))
        if t.get("max_billing_days") and days > t["max_billing_days"]:
            F.append(_f("days", "Potential Billing Discrepancy", "Billing period is longer than allowed",
                        days, t["max_billing_days"], days - t["max_billing_days"],
                        f"{days} days billed against a maximum of {t['max_billing_days']}.", ref,
                        "Ask the utility why the billing period exceeded the limit."))

    if history_avg and basis and basis > 1.5 * history_avg and basis - history_avg >= 20:
        F.append(_f("high_use", "No Discrepancy Found", "Consumption is higher than your usual",
                    basis, r2(history_avg), r2(basis - history_avg),
                    "Compared with the average of your earlier audited bills. High use alone is "
                    "NOT evidence of a billing error.", "n/a",
                    "Review appliance use and the meter readings before disputing the bill.",
                    counts=False, info=True))

    return _result(F, billed, units_calc, calc_total, total, expected_comp, ref, tariff,
                   sum_billed, arrears, credits,
                   checks=_checks(F, tariff, units_calc, expected_comp), parts=parts)


def _checks(F, tariff, units_calc, expected_comp):
    """Human-readable list of every check performed, skipped or failed."""
    by = {f["code"]: f for f in F}
    out = [dict(name="Required data present", outcome="pass", detail="Total bill amount supplied")]

    def add(name, code, ran=True, ok="Passed", skip="Not checked"):
        if not ran:
            out.append(dict(name=name, outcome="skip", detail=skip))
        elif code in by:
            out.append(dict(name=name, outcome="fail", detail=by[code]["title"]))
        else:
            out.append(dict(name=name, outcome="pass", detail=ok))

    add("Meter readings consistent", "reading_inconsistent", ok="Current reading is not below previous")
    add("Units match meter readings", "units_mismatch", units_calc is not None,
        "Billed units equal (current - previous) x multiplier", "Readings were inconsistent")
    add("Meter reading status", "meter_status", ok="Actual readings used")
    add("Charges add up to the total", "arithmetic", ok="Sum of charges equals the total within Rs 1")
    has_t = tariff is not None
    out.append(dict(name="Verified tariff available", outcome="pass" if has_t else "skip",
                    detail="Verified tariff found for this provider, category and date" if has_t
                    else "No verified tariff, so rate checks were skipped"))
    for k, lbl in COMPONENTS:
        add(f"{lbl} matches tariff", f"{k}_mismatch", has_t, "Within Rs 1 of the tariff calculation",
            "Needs a verified tariff")
    add("Billing period within limit", "days", bool(has_t and tariff.get("max_billing_days")),
        "Within the allowed number of days", "No limit on record")
    return out


def _result(F, billed, units_calc, calc_total, total, expected_comp, ref, tariff,
            sum_billed=None, arrears=0.0, credits=0.0, checks=None, parts=None):
    real = [f for f in F if not f["info"]]
    status = max((f["status"] for f in real), key=STATUSES.index) if real else "No Discrepancy Found"
    if calc_total is not None:
        overcharge = max(0.0, r2(total - calc_total))
    elif sum_billed is not None:
        overcharge = max(0.0, r2(total - sum_billed))
    else:
        overcharge = 0.0
    comps = [{"name": lbl, "billed": billed.get(k, 0.0),
              "expected": (expected_comp or {}).get(k)} for k, lbl in COMPONENTS]
    comps += [{"name": "Arrears", "billed": arrears, "expected": arrears if expected_comp else None},
              {"name": "Credits", "billed": -credits, "expected": -credits if expected_comp else None}]
    return dict(status=status, findings=F, units_calc=units_calc, billed_total=total,
                calc_total=calc_total, overcharge=overcharge, tariff_ref=ref,
                tariff_verified=tariff is not None, components=comps,
                issue_count=sum(1 for f in real if f["counts"]),
                checks=checks or [], slab_parts=parts or [])