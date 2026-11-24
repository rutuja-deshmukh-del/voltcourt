"""PDF audit report and complaint letter (reportlab). PDFs use 'Rs.' because built-in fonts lack the rupee sign."""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

S = getSampleStyleSheet()


def money(x):
    return "n/a" if x is None else f"Rs. {x:,.2f}"


def mask(n):
    n = str(n or "")
    return "*" * max(0, len(n) - 3) + n[-3:]


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("GRID", (0, 0), (-1, -1), .25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def report_pdf(rec, user_name):
    r, i = rec["result"], rec["inputs"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm)
    P = lambda t, s="BodyText": Paragraph(_esc(t), S[s])
    out = [P("VoltCourt - Electricity Bill Audit Report", "Title"),
           P(f"Audit ID {rec['id']}  |  Generated {date.today().isoformat()}  |  Account: {user_name}"),
           Spacer(1, 6),
           _table([["Item", "Value"],
                   ["Consumer number", mask(rec["consumer_no"])], ["Provider", rec["provider"] or "n/a"],
                   ["Bill date", rec["bill_date"]], ["Billing days", i.get("days")],
                   ["Units consumed (from readings)", r["units_calc"]],
                   ["Original bill amount", money(r["billed_total"])],
                   ["Independently calculated amount", money(r["calc_total"]) if r["calc_total"] is not None
                    else "Not calculated (tariff not verified)"],
                   ["Potential overcharge", money(r["overcharge"])],
                   ["Result", r["status"]],
                   ["Verification", "Verified tariff used" if r["tariff_verified"] else "Manual verification required"],
                   ["Tariff reference", r["tariff_ref"]]], [60 * mm, 110 * mm]),
           Spacer(1, 8), P("Charge comparison", "Heading2"),
           _table([["Charge", "Billed", "Expected"]] +
                  [[c["name"], money(c["billed"]), money(c["expected"])] for c in r["components"]],
                  [70 * mm, 50 * mm, 50 * mm]), Spacer(1, 8), P("Findings", "Heading2")]
    if not r["findings"]:
        out.append(P("No discrepancy found based on the checks performed."))
    for n, f in enumerate(r["findings"], 1):
        out += [P(f"{n}. {f['title']} [{f['status']}]", "Heading3"),
                P(f"Found: {f['found']}   Expected: {f['expected']}   Difference: {f['difference']}"),
                P(f"How calculated: {f['how']}"), P(f"Rule used: {f['rule']}"),
                P(f"What to do next: {f['next_step']}")]
    out += [Spacer(1, 10), P("This report is an automated check, not legal advice. A potential overcharge "
                             "is not a confirmed overcharge until the utility verifies it.", "Italic")]
    doc.build(out)
    return buf.getvalue()


def build_letter(rec, name, address, utility_office):
    r, i = rec["result"], rec["inputs"]
    issues = [f for f in r["findings"] if not f["info"]]
    lines = "\n".join(f"{n}. {f['title']}: billed {f['found']}, expected {f['expected']}"
                      + (f", difference {f['difference']}" if f["difference"] is not None else "")
                      + f". Basis: {f['how']}" for n, f in enumerate(issues, 1)) or "1. (describe the issue)"
    ver = ("The expected amounts use a verified tariff: " + r["tariff_ref"] if r["tariff_verified"]
           else "Note: the applicable tariff could not be verified in my check, so I request that you "
                "confirm the correct rates.")
    return (f"Date: {date.today().isoformat()}\n\nTo,\n{utility_office}\n{rec['provider'] or ''}\n\n"
            f"Subject: Request to review electricity bill - Consumer No. {rec['consumer_no']}, "
            f"bill dated {rec['bill_date']}\n\nSir/Madam,\n\n"
            f"I am {name}, consumer number {rec['consumer_no']}, residing at {address or '[address]'}. "
            f"I reviewed my bill dated {rec['bill_date']} for Rs. {r['billed_total']:,.2f} and found the "
            f"following points:\n\n{lines}\n\n{ver}\n\n"
            f"The estimated difference is Rs. {r['overcharge']:,.2f}.\n\n"
            "I request that you (1) explain these items in writing and (2) issue a corrected bill if any "
            "amount is found to be incorrect. A copy of my bill is attached as supporting evidence.\n\n"
            f"Yours faithfully,\n{name}\n[Signature]")


def letter_pdf(text):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm,
                            topMargin=20 * mm, bottomMargin=20 * mm)
    paras = []
    for block in text.split("\n\n"):
        paras += [Paragraph(_esc(block).replace("\n", "<br/>"), S["BodyText"]), Spacer(1, 6)]
    doc.build(paras)
    return buf.getvalue()