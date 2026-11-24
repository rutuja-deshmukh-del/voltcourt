import html
from datetime import date, datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from voltcourt import accounts, auth, engine, ocr, reports, store
from voltcourt.ui import PALETTE, PRIMARY, chip, ctitle, empty, goto, header, kpi, mask, pill, rupees

ORANGE, GREEN, PURPLE, RED = "#f97316", "#16a34a", "#7c3aed", "#dc2626"
METER = ["Normal", "Estimated", "Faulty / locked"]
OTHER = "Other / not listed"
DEFAULTS = dict(b_consumer="", b_prev=0.0, b_curr=0.0, b_mult=1.0, b_units=0.0, b_days=30, b_energy=0.0,
                b_fixed=0.0, b_wheeling=0.0, b_fac=0.0, b_duty=0.0, b_tax=0.0, b_arrears=0.0,
                b_credits=0.0, b_total=0.0, b_status="Normal", b_date=date.today())
MAP = dict(consumer_no="b_consumer", prev="b_prev", curr="b_curr", multiplier="b_mult", units="b_units",
           days="b_days", energy="b_energy", fixed="b_fixed", wheeling="b_wheeling", fac="b_fac",
           duty="b_duty", tax="b_tax", arrears="b_arrears", credits="b_credits", total="b_total",
           meter_status="b_status", bill_date="b_date")
INT_KEYS = {"b_days"}


# ============================ DASHBOARD ============================
STATUS_COLORS = {"No Discrepancy Found": "#22c55e", "Calculation Error": "#e11d48",
                 "Potential Billing Discrepancy": "#f97316", "Tariff Verification Required": "#eab308",
                 "Manual Review Required": "#8b5cf6", "Missing Information": "#3b82f6"}
COLS = ["id", "consumer_no", "bill_date", "created", "bill_amount", "calc_amount", "overcharge", "status",
        "issues", "units", "resolution", "provider"]
ICONS = {"Energy charge": "⚡", "Fixed charge": "📌", "Wheeling charge": "🔌", "Fuel adjustment charge": "⛽",
         "Electricity duty": "🏛️", "Tax": "🧾", "Arrears": "⏰"}
NEEDS_CHECK = ["Tariff Verification Required", "Manual Review Required", "Missing Information"]


def _delta(cur, prev, up_good=True):
    if not prev:
        return chip("New", "n") if cur else ""
    p = (cur - prev) / prev * 100
    return chip(f'{"▲" if p >= 0 else "▼"} {abs(p):.0f}%', "g" if (p >= 0) == up_good else "r")


def _grad(color):
    return alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0,
                        stops=[alt.GradientStop(color=color + "66", offset=0),
                               alt.GradientStop(color="#ffffff00", offset=1)])


def spark(values, color=PRIMARY):
    if len(values) < 2:
        st.caption("Trend appears after 2 audits.")
        return
    d = pd.DataFrame({"i": range(len(values)), "v": values})
    st.altair_chart(alt.Chart(d).mark_area(interpolate="monotone", line={"color": color}, color=_grad(color)).encode(
        x=alt.X("i:Q", axis=None), y=alt.Y("v:Q", axis=None)).properties(height=90), use_container_width=True)


def donut(df, col, height=230):
    d = df[col].value_counts().rename_axis(col).reset_index(name="n")
    scale = (alt.Scale(domain=list(STATUS_COLORS), range=list(STATUS_COLORS.values()))
             if col == "status" else alt.Scale(range=PALETTE))
    st.altair_chart(alt.Chart(d).mark_arc(innerRadius=58, cornerRadius=6, padAngle=0.02).encode(
        theta="n:Q", color=alt.Color(f"{col}:N", scale=scale, legend=alt.Legend(orient="bottom", title=None)),
        tooltip=[col, "n"]).properties(height=height), use_container_width=True)


def _mix(email, ids):
    tot = {}
    for i in ids[:20]:
        rec = store.get_audit(email, i)
        for c in rec["result"]["components"]:
            if c["billed"] > 0:
                tot[c["name"]] = tot.get(c["name"], 0) + c["billed"]
    return dict(sorted(tot.items(), key=lambda x: -x[1]))


def _alert(cls, title, value, share, color):
    return (f'<div class="alertb {cls}"><div class="at">{title}</div><div class="av">{value}</div>'
            f'<div class="sbar"><div style="width:{share:.0f}%;background:{color}"></div></div></div>')


def dashboard(u):
    rows = store.list_audits(u["email"])
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=COLS)
    n = len(df)
    df["m"] = df["created"].str[:7]
    this = date.today().strftime("%Y-%m")
    last = (date.today().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    cm, pm = df[df["m"] == this], df[df["m"] == last]
    header("Welcome to VoltCourt", "Your intelligent electricity bill auditing assistant.", ("＋ New audit", "Audit Bill"))
    q = st.columns(4)
    q[0].button("📤 Upload Electricity Bill", on_click=goto, args=("Audit Bill",), use_container_width=True)
    q[1].button("🧾 Start New Audit", on_click=goto, args=("Audit Bill",), use_container_width=True)
    q[2].button("🕑 View Audit History", on_click=goto, args=("My Audits",), use_container_width=True)
    q[3].button("✉️ Generate Complaint Letter", on_click=goto, args=("Complaint Letter",), use_container_width=True)
    st.write("")

    over, billed = float(df["overcharge"].sum()), float(df["bill_amount"].sum())
    clean = (df["status"] == "No Discrepancy Found").mean() * 100 if n else 0
    att = df[(df["resolution"] == "Pending verification") &
             ((df["overcharge"] > 0) | df["status"].isin(NEEDS_CHECK))]
    pend = df[df["resolution"].isin(["Pending verification", "Complaint filed"]) & (df["overcharge"] > 0)]
    conf = float(df.loc[df["resolution"] == "Resolved - bill corrected", "overcharge"].sum())
    k = st.columns(4)
    k[0].markdown(kpi("Bills audited", n, PRIMARY, "vs last month", "🧾", _delta(len(cm), len(pm))), unsafe_allow_html=True)
    k[1].markdown(kpi("Issues detected", int(df["issues"].sum()), ORANGE, "vs last month", "⚠️",
                      _delta(cm["issues"].sum(), pm["issues"].sum(), False)), unsafe_allow_html=True)
    k[2].markdown(kpi("Potential overcharges", rupees(over), RED,
                      f"{over / billed * 100:.1f}% of billed" if billed else "Unconfirmed", "💸"), unsafe_allow_html=True)
    k[3].markdown(kpi("Potential savings", rupees(pend["overcharge"].sum()), GREEN,
                      f"{len(pend)} pending · unconfirmed", "⏳"), unsafe_allow_html=True)
    st.write("")

    a, b = st.columns([1.7, 1], gap="large")
    with a, st.container(border=True):
        ctitle("Potential overcharge performance", "Audits (bars) and potential overcharge (area) by month")
        st.markdown(f'<div class="big">{rupees(over)}</div>', unsafe_allow_html=True)
        if n:
            m = df.groupby("m").agg(audits=("id", "count"), overcharge=("overcharge", "sum")).reset_index().sort_values("m")
            base = alt.Chart(m).encode(x=alt.X("m:N", title=None, sort=None, axis=alt.Axis(grid=False)))
            bars = base.mark_bar(color="#d9dbff", cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=24).encode(
                y=alt.Y("audits:Q", title=None, axis=alt.Axis(tickMinStep=1)), tooltip=["m", "audits"])
            area = base.mark_area(interpolate="monotone", line={"color": PRIMARY}, color=_grad(PRIMARY)).encode(
                y=alt.Y("overcharge:Q", title=None))
            pts = base.mark_point(color=PRIMARY, filled=True, size=70).encode(y="overcharge:Q", tooltip=["m", "overcharge"])
            st.altair_chart(alt.layer(bars, area, pts).resolve_scale(y="independent").properties(height=250),
                            use_container_width=True)
        else:
            empty("📊", "No activity yet", "Run your first audit to see activity here.")
    with b, st.container(border=True):
        ctitle("Where your money goes", "Charge mix across your recent audits")
        st.markdown(f'<div class="big">{rupees(billed)}</div>', unsafe_allow_html=True)
        mix = _mix(u["email"], list(df["id"])) if n else {}
        tot = sum(mix.values()) or 1
        if not mix:
            empty("🥧", "No breakdown yet", "Enter charges in an audit to see the mix.")
        for i, (name, amt) in enumerate(list(mix.items())[:5]):
            c = PALETTE[i % len(PALETTE)]
            st.markdown(f'<div class="brow"><div class="bic" style="background:{c}">{ICONS.get(name, "•")}</div>'
                        f'<div class="bmid"><div class="bl"><span>{name}</span><span><b>{rupees(amt)}</b>'
                        f'<i>{amt / tot * 100:.0f}%</i></span></div><div class="bbar"><div style="width:{amt / tot * 100:.0f}%;'
                        f'background:{c}"></div></div></div></div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    asc = df.sort_values("id")
    with c1, st.container(border=True):
        ctitle("🛡️ Clean-bill rate", "Share of audits with no discrepancy")
        st.markdown(f'<div class="big">{clean:.0f}%</div>', unsafe_allow_html=True)
        spark(list((asc["status"] == "No Discrepancy Found").astype(float).expanding().mean() * 100), GREEN)
    with c2, st.container(border=True):
        ctitle("⚡ Units per bill", "From meter readings")
        un = asc["units"].dropna()
        st.markdown(f'<div class="big">{un.mean():,.0f}</div>' if len(un) else '<div class="big">n/a</div>',
                    unsafe_allow_html=True)
        spark(list(un), PRIMARY)
    with c3, st.container(border=True):
        ctitle("⏳ Needs attention", "Pending audits")
        st.markdown(f'<div class="big">{len(att)}</div>', unsafe_allow_html=True)
        if att.empty:
            st.caption("Nothing pending 🎉")
        for _, r in att.head(2).iterrows():
            st.button(f"Open #{r['id']} · {r['status'][:22]}", key=f"att{r['id']}", on_click=goto, args=("Reports",),
                      kwargs={"open_audit": int(r["id"])}, use_container_width=True)
    with c4:
        if n and over > 0:
            body = (f'<small>✦ Insight</small><div class="iv">{rupees(over)}</div>'
                    f'<p>potential overcharge flagged across {int((df["overcharge"] > 0).sum())} audit(s). '
                    f'Unconfirmed until the utility verifies it.</p>')
        elif n:
            body = (f'<small>✦ Insight</small><div class="iv">{clean:.0f}%</div>'
                    '<p>of your audited bills had no discrepancy.</p>')
        else:
            body = '<small>✦ Insight</small><div class="iv">Start</div><p>Audit your first bill to see insights here.</p>'
        st.markdown(f'<div class="insight">{body}</div>', unsafe_allow_html=True)
        lid = int(df["id"].iloc[0]) if n else None
        st.button("View latest report →" if n else "Run your first audit →", on_click=goto,
                  args=("Reports" if n else "Audit Bill",), kwargs={"open_audit": lid} if n else {},
                  key="insight_btn", use_container_width=True)

    a, b = st.columns([1.5, 1], gap="large")
    with a, st.container(border=True):
        ctitle("Latest audits", "Your five most recent bills")
        if not n:
            empty("🧾", "No audits yet", "Open Audit Bill to run your first one.")
        for _, r in df.head(5).iterrows():
            st.markdown(f'<div class="row"><div class="rm"><div class="rav">#{r["id"]}</div><div>'
                        f'<b>{mask(r["consumer_no"])}</b><small>{r["bill_date"]} · {rupees(r["bill_amount"])}</small>'
                        f'</div></div>{pill(r["status"])}</div>', unsafe_allow_html=True)
    with b, st.container(border=True):
        ctitle("Alerts panel", "What deserves a look")
        d_n = int((df["overcharge"] > 0).sum())
        v_n = int(df["status"].isin(NEEDS_CHECK).sum())
        un_n = store.unread_count(u["email"])
        st.markdown(_alert("a-red", "Potential discrepancies", f"{d_n} audit(s)", d_n / n * 100 if n else 0, "#e11d48")
                    + _alert("a-amber", "Awaiting verification", f"{v_n} audit(s)", v_n / n * 100 if n else 0, "#f59e0b")
                    + _alert("a-blue", "Unread notifications", f"{un_n}", min(un_n * 20, 100), PRIMARY),
                    unsafe_allow_html=True)
        st.button("Open notifications →", on_click=goto, args=("Notifications",), use_container_width=True, key="al_btn")


# ============================ AUDIT BILL ============================
DEMO = dict(b_consumer="DEMO000001", b_prev=1000.0, b_curr=1250.0, b_mult=1.0, b_units=250.0, b_days=30,
            b_energy=1600.0, b_fixed=100.0, b_wheeling=250.0, b_fac=125.0, b_duty=207.5, b_tax=0.0,
            b_arrears=0.0, b_credits=0.0, b_total=2282.5, b_status="Normal")


def _apply_extraction(vals, conf, prov_names):
    low = []
    for k, v in vals.items():
        key = MAP.get(k)
        if k == "bill_date":
            try:
                v = datetime.fromisoformat(str(v)).date()
            except ValueError:
                continue
        elif key in INT_KEYS:
            v = int(v)
        elif k == "meter_status" and v not in METER:
            continue
        if key:
            st.session_state[key] = v
        if conf.get(k, 0) < 0.8:
            low.append(k)
    pv = vals.get("provider")
    if pv:
        m = [p for p in prov_names if pv.lower().split()[0] in p.lower()]
        if m:
            st.session_state["b_provider"] = m[0]
    return low


def _pick_conn(conns):
    c = next((x for x in conns if x["label"] == st.session_state.get("b_conn")), None)
    if c:
        st.session_state["b_consumer"] = c["consumer_no"]
        if c["provider"]:
            st.session_state["b_provider"] = c["provider"]
        if c["category"]:
            st.session_state["b_category"] = c["category"]


def _use_units():
    s = st.session_state
    s["b_units"] = engine.units_consumed(s["b_prev"], s["b_curr"], s["b_mult"])


def _clear():
    st.session_state.update(DEFAULTS)
    st.session_state["extracted"] = False


def _demo():
    st.session_state.update(DEMO)


def _stepper(extracted):
    def cls(i):
        return "done" if (i == 1 and extracted) else "active" if i == 2 else ""
    st.markdown('<div class="steps">'
                f'<div class="step {cls(1)}"><b>1</b>Upload bill (optional)</div>'
                f'<div class="step {cls(2)}"><b>2</b>Verify details</div>'
                '<div class="step"><b>3</b>Audit report</div></div>', unsafe_allow_html=True)


def _live_panel(tariff):
    s = st.session_state
    rows = []
    if s.b_curr < s.b_prev:
        rows.append((False, "Current reading is below the previous reading"))
    elif s.b_curr or s.b_prev:
        calc = engine.units_consumed(s.b_prev, s.b_curr, s.b_mult)
        ok = abs(calc - s.b_units) <= 0.5
        rows.append((ok, f"Units from readings: {calc:g}" + ("" if ok else f" · you entered {s.b_units:g}")))
    ssum = engine.r2(s.b_energy + s.b_fixed + s.b_wheeling + s.b_fac + s.b_duty + s.b_tax + s.b_arrears - s.b_credits)
    if s.b_total > 0:
        ok = abs(ssum - s.b_total) <= 1
        rows.append((ok, f"Charges add up to {rupees(ssum)}" + ("" if ok else f" · total entered {rupees(s.b_total)}")))
    rows.append((tariff is not None, "Verified tariff found: rates will be checked" if tariff
                 else "No verified tariff: only units and arithmetic will be checked"))
    done = [bool(s.b_consumer.strip()), s.b_curr > 0, s.b_units > 0, s.b_energy > 0, s.b_total > 0]
    st.progress(sum(done) / len(done), text=f"{sum(done) * 20}% of key fields filled")
    st.markdown("".join(f'<div class="live {"ok" if ok else "no"}">{"✔" if ok else "⚠"} {t}</div>' for ok, t in rows),
                unsafe_allow_html=True)


def audit_page(u):
    header("Audit a bill", "Upload or enter your bill, verify the values and run the audit.")
    for k, v in DEFAULTS.items():
        st.session_state.setdefault(k, v)
    provs = store.providers()
    names = [p["name"] for p in provs]
    cats = store.categories() + [OTHER]
    st.session_state.setdefault("b_provider", next((n for n in names if "MSEDCL" in n), names[0]))
    st.session_state.setdefault("b_category", cats[0])
    _stepper(st.session_state.get("extracted"))

    with st.container(border=True):
        st.markdown('<div class="dropicon">⬆</div><div class="droptitle">Drop your bill here</div>'
                    '<div class="dropsub">Get the values extracted automatically, or skip and type them in below.</div>',
                    unsafe_allow_html=True)
        up = st.file_uploader("Upload your bill (PDF, JPG or PNG, max 5 MB)", type=["pdf", "jpg", "jpeg", "png"],
                              key="bill_file", label_visibility="collapsed")
        if up is not None:
            data = up.getvalue()
            ok, msg, mt = ocr.validate_upload(up.name, data)
            if not ok:
                st.error(msg)
                store.notify(u["email"], "upload_failed", f"Upload rejected: {msg}")
            else:
                if mt == "application/pdf":
                    st.info(f"📄 {up.name} · {len(data) / 1024:,.0f} KB · PDF ready")
                else:
                    st.image(data, caption=up.name, width=360)
                if st.button("✨ Extract details from this bill", type="primary"):
                    with st.spinner("Reading your bill…"):
                        vals, conf, err = ocr.extract(data, mt)
                    if err:
                        st.warning(err)
                        if "ANTHROPIC_API_KEY" in err:
                            st.info("To switch on automatic extraction, create the file `.streamlit/secrets.toml` in your "
                                    "project folder with one line: `ANTHROPIC_API_KEY = \"your-key\"`, save it and restart "
                                    "the app. Until then, type the values from your bill below. The audit works the same.")
                    else:
                        st.session_state["low_conf"] = _apply_extraction(vals, conf, names)
                        st.session_state["extracted"] = True
                        st.rerun()
        if st.session_state.get("extracted"):
            st.success("Details extracted. Check every value below before auditing.")
            if st.session_state.get("low_conf"):
                st.warning("Low confidence, please verify: " + ", ".join(st.session_state["low_conf"]))

    st.markdown('<div class="hl">WHAT HAPPENS TO YOUR BILL</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    f1.markdown('<div class="fc"><div class="fi" style="background:#f3e8ff">🧠</div><div><b>AI extraction</b>'
                '<span>Reads readings and charges when you click Extract. Needs an API key.</span></div></div>',
                unsafe_allow_html=True)
    f2.markdown('<div class="fc"><div class="fi" style="background:#fff3e0">🧮</div><div><b>Independent maths</b>'
                '<span>Every figure is recalculated in plain code, never by AI.</span></div></div>', unsafe_allow_html=True)
    f3.markdown('<div class="fc"><div class="fi" style="background:#e6f7ec">🔒</div><div><b>Private</b>'
                '<span>Your file is checked and not stored by VoltCourt. Consumer numbers are masked.</span></div></div>',
                unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;margin:.8rem 0"><span style="color:#9ca3af;font-size:.78rem">'
                'Supported formats </span><span class="fmt">PDF</span><span class="fmt">PNG</span>'
                '<span class="fmt">JPG</span></div>', unsafe_allow_html=True)
    conns = store.connections(u["email"])
    left, right = st.columns([2, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("#### 🔌 Connection")
            if conns:
                st.selectbox("Saved connection", ["Enter manually"] + [c["label"] for c in conns], key="b_conn",
                             on_change=_pick_conn, args=(conns,))
            c = st.columns(3)
            c[0].text_input("Consumer number", key="b_consumer")
            c[1].selectbox("Electricity provider", names, key="b_provider")
            c[2].selectbox("Consumer category", cats, key="b_category")
            c = st.columns(3)
            c[0].date_input("Bill date", key="b_date")
            c[1].number_input("Billing days", min_value=1, step=1, key="b_days")
            c[2].selectbox("Meter reading status", METER, key="b_status")
        with st.container(border=True):
            st.markdown("#### ⚡ Meter readings")
            c = st.columns(4)
            c[0].number_input("Previous reading", min_value=0.0, key="b_prev")
            c[1].number_input("Current reading", min_value=0.0, key="b_curr")
            c[2].number_input("Meter multiplier", min_value=0.0, key="b_mult")
            c[3].number_input("Units billed", min_value=0.0, key="b_units")
            st.button("Use units calculated from readings", on_click=_use_units)
        with st.container(border=True):
            st.markdown("#### 💳 Charges on the bill")
            c = st.columns(3)
            c[0].number_input("Energy charge (₹)", min_value=0.0, key="b_energy")
            c[1].number_input("Fixed charge (₹)", min_value=0.0, key="b_fixed")
            c[2].number_input("Wheeling charge (₹)", min_value=0.0, key="b_wheeling")
            c = st.columns(3)
            c[0].number_input("Fuel adjustment charge (₹)", min_value=0.0, key="b_fac")
            c[1].number_input("Electricity duty (₹)", min_value=0.0, key="b_duty")
            c[2].number_input("Taxes (₹)", min_value=0.0, key="b_tax")
            c = st.columns(3)
            c[0].number_input("Arrears (₹)", min_value=0.0, key="b_arrears")
            c[1].number_input("Credits (₹)", min_value=0.0, key="b_credits")
            c[2].number_input("Total payable (₹)", min_value=0.0, key="b_total")
    s = st.session_state
    prov = next(p for p in provs if p["name"] == s.b_provider)
    tariff = store.find_tariff(prov["id"], s.b_category, s.b_date)
    with right, st.container(border=True):
        st.markdown("#### 🛡️ Live check")
        _live_panel(tariff)
        sure = st.checkbox("I have checked these values against my bill") if s.get("extracted") else True
        go = st.button("🔍 Run audit", type="primary", use_container_width=True)
        st.button("Clear form", on_click=_clear, use_container_width=True)
        st.button("Load demo values (not a real bill)", on_click=_demo, use_container_width=True)
    if not go:
        return
    if not s.b_consumer.strip() or s.b_total <= 0:
        st.error("Consumer number and total payable are required.")
        return
    if not sure:
        st.error("Please confirm you checked the extracted values.")
        return
    inp = dict(consumer_no=s.b_consumer.strip(), prev=s.b_prev, curr=s.b_curr, multiplier=s.b_mult,
               units=s.b_units, days=int(s.b_days), energy=s.b_energy, fixed=s.b_fixed,
               wheeling=s.b_wheeling, fac=s.b_fac, duty=s.b_duty, tax=s.b_tax, arrears=s.b_arrears,
               credits=s.b_credits, total=s.b_total, meter_status=s.b_status, bill_date=str(s.b_date),
               category=s.b_category)
    res = engine.audit(inp, tariff, store.avg_units(u["email"], inp["consumer_no"]))
    cid = next((x["id"] for x in conns if x["consumer_no"] == inp["consumer_no"]), None)
    aid = store.save_audit(u["email"], inp, res, prov["id"], cid)
    store.notify(u["email"], "audit_done", f"Audit #{aid} completed: {res['status']}.")
    if res["issue_count"]:
        store.notify(u["email"], "discrepancy", f"Audit #{aid}: {res['issue_count']} potential issue(s) found.")
    if res["status"] in ("Tariff Verification Required", "Manual Review Required", "Missing Information"):
        store.notify(u["email"], "pending", f"Audit #{aid} needs manual verification.")
    store.notify(u["email"], "report", f"Report for audit #{aid} is ready to download.")
    st.session_state["extracted"] = False
    goto("Reports", open_audit=aid)
    st.toast("Audit saved ✅")
    st.rerun()


# ============================ REPORTS ============================
VERDICT = {"No Discrepancy Found": ("✅", "No discrepancy found", "ok"),
           "Calculation Error": ("❌", "Calculation error found", "bad"),
           "Potential Billing Discrepancy": ("⚠️", "Potential billing discrepancy", "bad"),
           "Tariff Verification Required": ("🔎", "Tariff verification required", "warn"),
           "Manual Review Required": ("🧐", "Manual review required", "warn"),
           "Missing Information": ("ℹ️", "More information needed", "info")}
RECOMMEND = {
    "No Discrepancy Found": ["Keep this report with your bill for your records.",
                             "Compare future bills against this one to spot unusual jumps."],
    "Calculation Error": ["Ask the utility for a line-by-line explanation of how the total was derived.",
                          "Request a corrected bill if the arithmetic cannot be justified.",
                          "Check the due date and the utility's process for disputing a bill."],
    "Potential Billing Discrepancy": ["Generate the complaint letter and review it before sending.",
                                      "Ask which tariff clause supports each flagged amount.",
                                      "Attach a copy of the bill and this report as supporting evidence."],
    "Tariff Verification Required": ["Ask an administrator to add the verified tariff for this provider, category and period.",
                                     "Run the audit again once the tariff is verified.",
                                     "Until then, treat rate-related results as unchecked."],
    "Manual Review Required": ["Resolve the flagged item (readings or meter status) with the utility first.",
                               "Ask for an actual meter reading if the bill was estimated."],
    "Missing Information": ["Enter the missing values from your bill and audit again."]}


def _summary(r):
    s = r["status"]
    if s == "No Discrepancy Found":
        return "Every check that could be run passed, and your bill matches the verified tariff."
    if s in ("Calculation Error", "Potential Billing Discrepancy"):
        return (f"{r['issue_count']} issue(s) found. The potential difference is {rupees(r['overcharge'])}, "
                "which stays unconfirmed until the utility verifies it.")
    if s == "Tariff Verification Required":
        return "Rates could not be verified, so only units and arithmetic were checked."
    if s == "Manual Review Required":
        return "Something on the bill needs a human check before it can be audited fully."
    return "The audit needs more information from the bill."


def _pick_audit(u, key):
    rows = store.list_audits(u["email"])
    if not rows:
        return None
    ids = [r["id"] for r in rows]
    cur = st.session_state.get("open_audit")
    idx = ids.index(cur) if cur in ids else 0
    aid = st.selectbox("Audit", ids, index=idx, key=key,
                       format_func=lambda i: next(f"#{r['id']} · {mask(r['consumer_no'])} · {r['bill_date']} · {r['status']}"
                                                  for r in rows if r["id"] == i))
    st.session_state["open_audit"] = aid
    return store.get_audit(u["email"], aid)


def _finding_card(f):
    tone = {"Calculation Error": "bad", "Potential Billing Discrepancy": "bad", "Tariff Verification Required": "warn",
            "Manual Review Required": "warn", "Missing Information": "info"}.get(f["status"], "info")
    e = html.escape
    st.markdown(
        f'<div class="fcard {tone}"><div class="ft"><span>{e(f["title"])}</span>{pill(f["status"])}</div>'
        f'<div class="fgrid"><div><small>Found</small>{e(str(f["found"]))}</div>'
        f'<div><small>Expected</small>{e(str(f["expected"]))}</div>'
        f'<div><small>Difference</small>{e(str(f["difference"]))}</div></div>'
        f'<p><b>How it was calculated:</b> {e(str(f["how"]))}</p>'
        f'<p><b>Rule used:</b> {e(str(f["rule"]))}</p>'
        f'<p><b>What to do next:</b> {e(str(f["next_step"]))}</p></div>', unsafe_allow_html=True)


def _score(r):
    ch = r.get("checks") or []
    p = sum(c["outcome"] == "pass" for c in ch)
    f = sum(c["outcome"] == "fail" for c in ch)
    s = sum(c["outcome"] == "skip" for c in ch)
    return (round(p / (p + f) * 100) if p + f else None), p, f, s


def reports_page(u):
    header("Audit report", "An independent check of your electricity bill")
    rec = _pick_audit(u, "rep_pick")
    if not rec:
        empty("📑", "No reports yet", "Run an audit and your report appears here.")
        return
    r, inp = rec["result"], rec["inputs"]
    icon, head, tone = VERDICT[r["status"]]
    st.markdown(f'<div class="meta"><div>Audit ID<b>#{rec["id"]}</b></div><div>Consumer<b>{mask(rec["consumer_no"])}</b></div>'
                f'<div>Provider<b>{html.escape(str(rec["provider"]))}</b></div><div>Bill date<b>{rec["bill_date"]}</b></div>'
                f'<div>Audited on<b>{rec["created"][:10]}</b></div></div>', unsafe_allow_html=True)
    pct, np_, nf, ns = _score(r)
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        st.markdown(f'<div class="vbanner {tone}"><h2>{icon} {head.upper()}</h2><p>{_summary(r)}</p></div>',
                    unsafe_allow_html=True)
        st.write("")
        b = st.columns(3)
        b[0].download_button("⬇️ Download PDF", reports.report_pdf(rec, u["name"]), f"audit_{rec['id']}.pdf",
                             "application/pdf", use_container_width=True)
        b[1].button("✉️ Generate complaint", on_click=goto, args=("Complaint Letter",), use_container_width=True)
        with b[2]:
            components.html('<button onclick="window.parent.print()" style="width:100%;padding:.55rem;'
                            'border:1px solid #e3e6ef;border-radius:12px;background:#fff;font-weight:600;'
                            'cursor:pointer">🖨️ Print report</button>', height=48)
    with right, st.container(border=True):
        col = "#22c55e" if (pct or 0) >= 80 else "#f59e0b" if (pct or 0) >= 50 else "#e11d48"
        st.markdown(f'<div class="scorebox"><div class="ctitle">Audit score</div>'
                    f'<div class="sv">{"n/a" if pct is None else f"{pct}/100"}</div>'
                    f'<div class="sbar"><div style="width:{pct or 0}%;background:{col}"></div></div>'
                    f'<div class="sstat"><span>Checks passed</span><b>{np_}</b></div>'
                    f'<div class="sstat"><span>Checks failed</span><b>{nf}</b></div>'
                    f'<div class="sstat"><span>Skipped</span><b>{ns}</b></div></div>', unsafe_allow_html=True)
        st.caption("Score = share of checks passed. Skipped checks are not counted.")
    st.write("")

    t = st.tabs(["Overview", "Charges", "Findings", "Calculation", "Next steps"])
    with t[0]:
        k = st.columns(4)
        k[0].markdown(kpi("Units (from readings)", r["units_calc"] if r["units_calc"] is not None else "n/a",
                          PRIMARY, icon="⚡"), unsafe_allow_html=True)
        k[1].markdown(kpi("Original bill", rupees(r["billed_total"]), ORANGE, icon="🧾"), unsafe_allow_html=True)
        k[2].markdown(kpi("Independent calculation", rupees(r["calc_total"]), GREEN,
                          "" if r["calc_total"] is not None else "Tariff not verified", "🧮"), unsafe_allow_html=True)
        k[3].markdown(kpi("Potential overcharge", rupees(r["overcharge"]), RED, "Unconfirmed", "💸"), unsafe_allow_html=True)
        st.write("")
        c1, c2 = st.columns([1.4, 1], gap="large")
        with c1, st.container(border=True):
            ctitle("Top findings", "What the audit flagged")
            real = [f for f in r["findings"] if not f["info"]]
            if not real:
                st.success("No discrepancy found based on the checks performed.")
            for f in real[:3]:
                tag = "t-fail" if f["counts"] else "t-skip"
                st.markdown(f'<div class="mini"><span class="mt {tag}">{html.escape(f["status"])}</span>'
                            f'<b>{html.escape(f["title"])}</b><small>{html.escape(str(f["how"]))}</small></div>',
                            unsafe_allow_html=True)
            comp = pd.DataFrame([{"Charge": c["name"], "Amount": c["billed"]} for c in r["components"] if c["billed"] > 0])
            if not comp.empty:
                st.markdown("**Where your bill goes**")
                st.altair_chart(alt.Chart(comp).mark_arc(innerRadius=55, cornerRadius=6, padAngle=0.02).encode(
                    theta="Amount:Q", color=alt.Color("Charge:N", scale=alt.Scale(range=PALETTE),
                                                      legend=alt.Legend(orient="bottom", title=None)),
                    tooltip=["Charge", "Amount"]).properties(height=240), use_container_width=True)
        with c2, st.container(border=True):
            ctitle("Checks snapshot", "Failed checks first")
            ch = sorted(r.get("checks") or [], key=lambda c: {"fail": 0, "pass": 1, "skip": 2}[c["outcome"]])
            if not ch:
                st.caption("This older audit has no check list. Run a new audit to see it.")
            lab = {"pass": "PASSED", "fail": "FAILED", "skip": "SKIPPED"}
            for c in ch[:6]:
                st.markdown(f'<div class="mini"><span class="mt t-{c["outcome"]}">{lab[c["outcome"]]}</span>'
                            f'<b>{html.escape(c["name"])}</b><small>{html.escape(c["detail"])}</small></div>',
                            unsafe_allow_html=True)
    with t[1]:
        rows = []
        for c in r["components"]:
            if c["name"] == "Credits":
                continue
            exp = c["expected"]
            var = None if exp is None else round(c["billed"] - exp, 2)
            rows.append({"Charge": c["name"], "Billed (₹)": c["billed"], "Expected (₹)": exp, "Variance (₹)": var,
                         "Result": "Not verified" if exp is None else ("✅ Match" if abs(var) <= engine.TOL else "⚠️ Mismatch")})
        d = pd.DataFrame(rows)
        if d["Expected (₹)"].notna().any():
            long = d.melt(id_vars=["Charge"], value_vars=["Billed (₹)", "Expected (₹)"], var_name="Type", value_name="Amount")
            long["Type"] = long["Type"].str.replace(" (₹)", "", regex=False)
            st.altair_chart(alt.Chart(long.dropna()).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                x=alt.X("Charge:N", sort=None, title=None), y=alt.Y("Amount:Q", title="₹"),
                color=alt.Color("Type:N", scale=alt.Scale(domain=["Billed", "Expected"], range=["#f97316", PRIMARY]),
                                legend=alt.Legend(orient="bottom", title=None)),
                xOffset="Type:N", tooltip=["Charge", "Type", "Amount"]).properties(height=280), use_container_width=True)
        else:
            st.info("Expected amounts need a verified tariff, so only the billed charges are shown.")
        st.dataframe(d, use_container_width=True, hide_index=True)
    with t[2]:
        if not r["findings"]:
            st.success("No discrepancy found based on the checks performed.")
        for f in r["findings"]:
            _finding_card(f)
    with t[3]:
        with st.container(border=True):
            st.markdown("**Units consumed**")
            st.code(f"({inp.get('curr')} - {inp.get('prev')}) x {inp.get('multiplier', 1)} = {r['units_calc']} units",
                    language=None)
            st.markdown("**Tariff reference**")
            st.caption(r["tariff_ref"])
            st.markdown("**Verification status:** " + ("✅ Verified tariff used" if r["tariff_verified"]
                                                       else "⚠️ Manual verification required"))
        if r.get("slab_parts"):
            st.markdown("**Energy slab calculation**")
            st.dataframe(pd.DataFrame(r["slab_parts"]).rename(columns={"from": "From", "to": "To", "units": "Units",
                                                                       "rate": "Rate (₹/unit)", "amount": "Amount (₹)"}),
                         use_container_width=True, hide_index=True)
        st.markdown("**All checks performed**")
        icons = {"pass": "✔", "fail": "✖", "skip": "–"}
        st.markdown("".join(f'<div class="chk {c["outcome"]}"><span class="ci">{icons[c["outcome"]]}</span>'
                            f'<div><b>{html.escape(c["name"])}</b><br><small>{html.escape(c["detail"])}</small></div></div>'
                            for c in r.get("checks") or []), unsafe_allow_html=True)
        st.caption("Every figure comes from the tariff record and the values you entered. No AI maths is used.")
    with t[4]:
        st.markdown("#### Recommended actions")
        for step in RECOMMEND[r["status"]]:
            st.markdown(f"- {step}")
        st.markdown("#### Track this audit")
        new = st.selectbox("Status of this audit", store.RESOLUTIONS, index=store.RESOLUTIONS.index(rec["resolution"]),
                           key=f"res_{rec['id']}")
        if new != rec["resolution"]:
            store.set_resolution(u["email"], rec["id"], new)
            st.toast("Saved")
            st.rerun()
        st.caption("Automated check, not legal advice. A potential overcharge is not confirmed until the utility verifies it.")


# ============================ MY AUDITS ============================
def my_audits(u):
    header("My audits", "Search, filter and open every audit you have run.")
    rows = store.list_audits(u["email"])
    if not rows:
        empty("🕑", "No audits yet", "Your audit history appears here.")
        return
    df = pd.DataFrame(rows)
    with st.container(border=True):
        c = st.columns([2, 2, 2, 2])
        q = c[0].text_input("Search (ID or consumer no)", placeholder="Search…", key="hist_q")
        stt = c[1].multiselect("Status", sorted(df["status"].unique()))
        res = c[2].multiselect("Resolution", store.RESOLUTIONS)
        sort = c[3].selectbox("Sort by", ["Newest", "Oldest", "Highest overcharge", "Highest bill"])
        d = st.date_input("Audit date range", value=(), key="hist_dates")
    if q:
        df = df[df["consumer_no"].str.contains(q, case=False) | (df["id"].astype(str) == q.strip("# "))]
    if stt:
        df = df[df["status"].isin(stt)]
    if res:
        df = df[df["resolution"].isin(res)]
    if len(d) == 2:
        day = pd.to_datetime(df["created"]).dt.date
        df = df[(day >= d[0]) & (day <= d[1])]
    key, asc = {"Newest": ("id", False), "Oldest": ("id", True), "Highest overcharge": ("overcharge", False),
                "Highest bill": ("bill_amount", False)}[sort]
    df = df.sort_values(key, ascending=asc)
    size = 10
    pages = max(1, -(-len(df) // size))
    pg = st.number_input("Page", 1, pages, 1) if pages > 1 else 1
    view = df.iloc[(pg - 1) * size: pg * size]
    show = pd.DataFrame({"Audit ID": view["id"], "Consumer no": view["consumer_no"].map(mask),
                         "Provider": view["provider"], "Bill date": view["bill_date"],
                         "Audit date": view["created"].str[:10], "Bill (₹)": view["bill_amount"],
                         "Potential discrepancy (₹)": view["overcharge"], "Status": view["status"],
                         "Resolution": view["resolution"]})
    st.dataframe(show, use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} audit(s) · page {pg} of {pages}")
    if len(view):
        aid = st.selectbox("Open an audit", list(view["id"]), key="hist_pick")
        rec = store.get_audit(u["email"], aid)
        b = st.columns(3)
        b[0].button("📑 View report", on_click=goto, args=("Reports",), kwargs={"open_audit": aid},
                    use_container_width=True)
        b[1].download_button("⬇️ Download PDF", reports.report_pdf(rec, u["name"]), f"audit_{aid}.pdf",
                             "application/pdf", use_container_width=True)
        b[2].button("✉️ Generate complaint", on_click=goto, args=("Complaint Letter",),
                    kwargs={"open_audit": aid}, use_container_width=True)


# ============================ COMPLAINT ============================
def complaint_page(u):
    header("Complaint letter", "Turn an audit into a polite, editable letter to your utility.")
    rec = _pick_audit(u, "cmp_pick")
    if not rec:
        empty("✉️", "No audit selected", "Run an audit first.")
        return
    r = rec["result"]
    if r["status"] == "No Discrepancy Found":
        st.info("This audit found no discrepancy, so there is nothing to complain about.")
        return
    unverified = (not r["tariff_verified"]) or r["status"] in (
        "Tariff Verification Required", "Manual Review Required", "Missing Information")
    if unverified:
        st.warning("This audit is based on an unverified discrepancy (tariff not verified or manual review "
                   "needed). The letter will ask the utility to confirm, not accuse it.")
        if not st.checkbox("I understand and want to generate a complaint anyway"):
            return
    c = st.columns(2)
    addr = c[0].text_area("Your address", height=90)
    office = c[1].text_input("Addressed to", "The Executive Engineer")
    st.session_state.setdefault("letter_for", None)
    if st.session_state["letter_for"] != (rec["id"], addr, office):
        st.session_state["letter_text"] = reports.build_letter(rec, u["name"], addr, office)
        st.session_state["letter_for"] = (rec["id"], addr, office)
    text = st.text_area("Review and edit before sending", key="letter_text", height=420)
    t1, t2 = st.tabs(["Preview", "Copy"])
    with t1, st.container(border=True):
        st.text(text)
    with t2:
        st.code(text, language=None)
    b = st.columns(3)
    b[0].download_button("⬇️ Download PDF", reports.letter_pdf(text), f"complaint_{rec['id']}.pdf",
                         "application/pdf", use_container_width=True)
    if b[1].button("💾 Save letter", use_container_width=True):
        store.save_complaint(u["email"], rec["id"], text)
        st.toast("Letter saved")
    b[2].caption("To print, download the PDF and print it.")
    st.caption("Not legal advice. Review the letter and send it yourself. Attach a copy of your bill.")
    old = [x for x in store.list_complaints(u["email"]) if x["audit_id"] == rec["id"]]
    if old:
        with st.expander(f"Saved letters for this audit ({len(old)})"):
            for x in old:
                st.caption(x["created"])
                st.code(x["body"], language=None)


# ============================ ANALYTICS ============================
def analytics_page(u):
    header("Analytics", "Consumption, charge mix, comparisons and overcharge tracking.")
    rows = store.list_audits(u["email"])
    if not rows:
        empty("📊", "No data yet", "Audit at least one bill to see analytics.")
        return
    df = pd.DataFrame(rows)
    t1, t2, t3, t4 = st.tabs(["Consumption", "Charge mix", "Compare bills", "Overcharge tracker"])
    with t1:
        no = st.selectbox("Connection", sorted(df["consumer_no"].unique()), format_func=mask)
        d = df[df["consumer_no"] == no].dropna(subset=["units"]).sort_values("bill_date")
        if d.empty:
            st.info("No unit data for this connection.")
        else:
            u_ = d.set_index("bill_date")["units"]
            k = st.columns(4)
            k[0].markdown(kpi("Average units", f"{u_.mean():,.0f}", icon="📊"), unsafe_allow_html=True)
            k[1].markdown(kpi("Highest", f"{u_.max():,.0f}", ORANGE, str(u_.idxmax()), icon="🔺"), unsafe_allow_html=True)
            k[2].markdown(kpi("Lowest", f"{u_.min():,.0f}", GREEN, str(u_.idxmin()), icon="🔻"), unsafe_allow_html=True)
            k[3].markdown(kpi("Est. annual units", f"{u_.mean() * 12:,.0f}", PURPLE, "Average x 12", icon="📅"),
                          unsafe_allow_html=True)
            d2 = d[["bill_date", "units"]]
            line = alt.Chart(d2).mark_line(point=True, color="#635bff").encode(
                x=alt.X("bill_date:T", title=None), y=alt.Y("units:Q", title="Units"), tooltip=["bill_date", "units"])
            avg = alt.Chart(pd.DataFrame({"y": [u_.mean()]})).mark_rule(strokeDash=[6, 4], color="#f97316").encode(y="y:Q")
            st.altair_chart((line + avg).properties(height=280), use_container_width=True)
            st.caption("Dashed line = your average. High use alone is not a billing error.")
            if len(u_) > 1:
                st.dataframe(pd.DataFrame({"Units": u_, "Change": u_.diff(), "Change %": (u_.pct_change() * 100).round(1)}),
                             use_container_width=True)
    with t2:
        recs = [store.get_audit(u["email"], i) for i in df["id"].head(12)]
        recs = sorted(recs, key=lambda r: r["bill_date"])
        long = pd.DataFrame([{"Bill": f"{r['bill_date']} (#{r['id']})", "Charge": c["name"], "Amount": c["billed"]}
                             for r in recs for c in r["result"]["components"] if c["billed"] > 0])
        if long.empty:
            st.info("No charge breakdown available yet.")
        else:
            st.altair_chart(alt.Chart(long).mark_bar().encode(
                x=alt.X("Bill:N", sort=None, title=None), y=alt.Y("Amount:Q", title="₹"),
                color=alt.Color("Charge:N", legend=alt.Legend(orient="bottom", title=None)),
                tooltip=["Bill", "Charge", "Amount"]).properties(height=300), use_container_width=True)
    with t3:
        ids = st.multiselect("Select two or more audits", list(df["id"]),
                             format_func=lambda i: f"#{i} · {df.loc[df['id'] == i, 'bill_date'].iloc[0]}")
        if len(ids) < 2:
            st.info("Pick at least two audits to compare.")
        else:
            recs = sorted((store.get_audit(u["email"], i) for i in ids), key=lambda r: r["bill_date"])
            tab = {"Units": [r["result"]["units_calc"] for r in recs],
                   "Total bill (₹)": [r["result"]["billed_total"] for r in recs]}
            for i, comp in enumerate(recs[0]["result"]["components"]):
                tab[comp["name"] + " (₹)"] = [r["result"]["components"][i]["billed"] for r in recs]
            t = pd.DataFrame(tab, index=[f"{r['bill_date']} (#{r['id']})" for r in recs]).T
            t["Change (last vs first)"] = t.iloc[:, -1] - t.iloc[:, 0]
            st.dataframe(t, use_container_width=True)
            for a, b in zip(recs, recs[1:]):
                ta, tb = a["result"]["billed_total"], b["result"]["billed_total"]
                if ta and tb > ta * 1.3:
                    st.warning(f"Bill rose {((tb / ta) - 1) * 100:.0f}% from {a['bill_date']} to {b['bill_date']}. "
                               "Check units first: high use is not the same as a billing error.")
    with t4:
        pend = df[df["resolution"].isin(["Pending verification", "Complaint filed"])]
        done = df[df["resolution"] == "Resolved - bill corrected"]
        k = st.columns(4)
        k[0].markdown(kpi("Potential overcharges", rupees(df["overcharge"].sum()), RED, icon="💸"), unsafe_allow_html=True)
        k[1].markdown(kpi("Pending verification", len(pend), PURPLE, icon="⏳"), unsafe_allow_html=True)
        k[2].markdown(kpi("Closed", int(df["resolution"].str.startswith(("Resolved", "Dismissed")).sum()), GREEN, icon="🔒"),
                      unsafe_allow_html=True)
        k[3].markdown(kpi("Confirmed recovered", rupees(done["overcharge"].sum()), GREEN, icon="🎯"), unsafe_allow_html=True)
        st.caption("Potential amounts are not savings until a bill is corrected.")
        c1, c2 = st.columns([1, 2], gap="large")
        with c1:
            donut(df, "resolution")
        with c2:
            st.dataframe(df[["id", "bill_date", "overcharge", "status", "resolution"]].rename(
                columns={"id": "Audit", "bill_date": "Bill date", "overcharge": "Potential (₹)",
                         "status": "Status", "resolution": "Resolution"}), use_container_width=True, hide_index=True)


# ============================ EXPLAIN ============================
GLOSSARY = {
    "What are fixed charges?": "Fixed charges are a set amount billed each period for having the connection, "
                               "whatever you consume. They usually depend on your category and sanctioned load.",
    "What is FAC?": "FAC means fuel adjustment charge. It is a per-unit amount added to recover changes in "
                    "power purchase cost. Check your bill for the rate and units it was applied to.",
    "How are energy charges calculated?": "Energy charge is units consumed split into slabs, each slab "
                                          "multiplied by its rate, then added up.",
    "What does my meter reading mean?": "Units consumed = (current reading - previous reading) x meter "
                                        "multiplier. The multiplier is 1 for most household meters.",
}


def explain_page(u):
    header("Explain my bill", "Plain-language answers based on your latest audit.")
    q = st.selectbox("Ask a question", ["Why is my electricity bill high?", "Why did my bill increase this month?"]
                     + list(GLOSSARY), key="ex_q")
    custom = st.text_input("…or type your own question")
    rec = None
    rows = store.list_audits(u["email"])
    if rows:
        rec = store.get_audit(u["email"], rows[0]["id"])
    question = custom or q
    ctx = "No audited bill yet."
    if rec:
        r = rec["result"]
        ctx = (f"Latest audited bill: units {r['units_calc']}, total {r['billed_total']}, status {r['status']}. "
               f"Charges: " + "; ".join(f"{c['name']}={c['billed']}" for c in r["components"]) +
               f". Tariff: {r['tariff_ref']}")
        if r["tariff_verified"]:
            ctx += " Slabs are in the verified tariff."
    if st.button("Explain", type="primary"):
        if question in GLOSSARY and not custom:
            st.info(GLOSSARY[question])
        elif not custom and len(rows) >= 2 and question.startswith("Why"):
            a, b = store.get_audit(u["email"], rows[1]["id"]), rec
            ua, ub = a["result"]["units_calc"], b["result"]["units_calc"]
            if ua and ub:
                st.info(f"Your units went from {ua:g} (bill {a['bill_date']}) to {ub:g} (bill {b['bill_date']}), "
                        f"a change of {ub - ua:+g} units. A bill rises mainly when units rise, because energy "
                        "charges grow with consumption. A higher bill alone does not prove an error.")
            else:
                st.info("Units could not be compared for your last two bills.")
        else:
            with st.spinner("Thinking…"):
                ans = ocr.ask(question, ctx)
            st.info(ans or "Add an ANTHROPIC_API_KEY in .streamlit/secrets.toml for custom questions, "
                           "or pick one of the built-in questions.")
        st.caption("General explanation based on your latest audited bill. Not legal advice.")


# ============================ NOTIFICATIONS ============================
def notifications_page(u):
    header("Notifications", "Audit results and alerts.")
    ns = store.notifications(u["email"])
    if not ns:
        empty("🔔", "No notifications", "Audit results and alerts show up here.")
        return
    if st.button("Mark all as read"):
        store.mark_all_read(u["email"])
        st.rerun()
    for x in ns:
        st.markdown(f'<div class="row"><span>{"🔵 " if not x["is_read"] else ""}{x["message"]}</span>'
                    f'<small>{x["created"][:16]}</small></div>', unsafe_allow_html=True)


# ============================ PROFILE ============================
def profile_page(u):
    header("Profile", "Your account, password and electricity connections.")
    with st.container(border=True):
        st.markdown(f"**Name:** {u['name']}  \n**Email:** {u['email']}  \n**Role:** {u['role']}")
    with st.container(border=True):
        st.markdown("#### Change password")
        with st.form("chpw", border=False):
            old = st.text_input("Current password", type="password")
            new = st.text_input("New password", type="password")
            new2 = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Update password", type="primary"):
                if new != new2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = accounts.change_password(u["email"], old, new)
                    (st.success if ok else st.error)(msg)
    with st.container(border=True):
        st.markdown("#### My connections (multiple consumer numbers)")
        provs = store.providers()
        with st.form("addconn", border=False):
            c = st.columns(4)
            no = c[0].text_input("Consumer number")
            lab = c[1].text_input("Label (e.g. Home)")
            pv = c[2].selectbox("Provider", [p["name"] for p in provs])
            cat = c[3].selectbox("Category", store.categories() + [OTHER])
            if st.form_submit_button("Add connection"):
                if no.strip():
                    p = next(x for x in provs if x["name"] == pv)
                    st.success("Added.") if store.add_connection(u["email"], no, lab, p["id"], cat) else st.error("Already added.")
        for c in store.connections(u["email"]):
            a, b = st.columns([5, 1])
            a.markdown(f'<div class="row"><span><b>{c["label"]}</b> · {mask(c["consumer_no"])} · {c["provider"]}</span></div>',
                       unsafe_allow_html=True)
            b.button("Remove", key=f"rm{c['id']}", on_click=store.delete_connection, args=(u["email"], c["id"]))


# ============================ ADMIN ============================
def admin_page(u):
    if u["role"] != "admin":
        st.error("Administrators only.")
        return
    header("Admin", "Users, providers, tariffs and system health.")
    t = st.tabs(["Statistics", "Users", "Providers & tariffs", "Errors"])
    with t[0]:
        cols = st.columns(3)
        for i, (k, v) in enumerate(store.admin_stats().items()):
            cols[i % 3].markdown(kpi(k, v), unsafe_allow_html=True)
    with t[1]:
        users = accounts.list_users()
        st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)
        c = st.columns(3)
        em = c[0].selectbox("User", [x["email"] for x in users])
        rl = c[1].selectbox("Role", ["user", "admin"])
        if c[2].button("Set role"):
            if em == u["email"] and rl != "admin":
                st.error("You cannot remove your own admin role.")
            else:
                accounts.set_role(em, rl)
                st.success("Updated.")
    with t[2]:
        provs = store.providers()
        with st.expander("Add provider"):
            with st.form("addprov"):
                n, s = st.text_input("Provider name"), st.text_input("State", "Maharashtra")
                if st.form_submit_button("Add") and n.strip():
                    store.add_provider(n, s)
                    st.rerun()
        st.markdown("#### Add tariff record")
        st.caption("Enter ONLY values copied from the official tariff order. Nothing is seeded or guessed. "
                   "Unverified tariffs are never used in audits.")
        with st.form("addtariff"):
            c = st.columns(3)
            pv = c[0].selectbox("Provider", [p["name"] for p in provs])
            cat = c[1].text_input("Consumer category", placeholder="e.g. LT-I Residential")
            src = c[2].text_input("Official source document (title / order no. / URL)")
            c = st.columns(3)
            ef = c[0].date_input("Effective from", value=date(2024, 1, 1))
            has_end = c[1].checkbox("Has expiry date")
            et = c[2].date_input("Effective to", value=date.today())
            st.markdown("Energy slabs (leave 'Up to units' empty on the LAST row)")
            slabs = st.data_editor(pd.DataFrame({"Up to units": [None], "Rate per unit (₹)": [0.0]}),
                                   num_rows="dynamic", use_container_width=True, key="slab_ed")
            c = st.columns(4)
            fixed = c[0].number_input("Fixed charge (₹)", min_value=0.0)
            prorate = c[1].number_input("Prorate fixed over N days (0 = no)", min_value=0, step=1)
            wh = c[2].number_input("Wheeling ₹/unit", min_value=0.0, format="%.4f")
            fac = c[3].number_input("FAC ₹/unit", min_value=0.0, format="%.4f")
            c = st.columns(4)
            duty = c[0].number_input("Electricity duty %", min_value=0.0)
            base = c[1].selectbox("Duty/tax applies to", ["all", "energy"],
                                  format_func=lambda x: "Energy + fixed + wheeling + FAC" if x == "all" else "Energy only")
            tax = c[2].number_input("Tax %", min_value=0.0)
            mx = c[3].number_input("Max billing days (0 = none)", min_value=0, step=1)
            ver = st.checkbox("I verified these values against the source document")
            if st.form_submit_button("Save tariff", type="primary"):
                rows_ = [(None if pd.isna(a) else float(a), float(b)) for a, b in
                         zip(slabs["Up to units"], slabs["Rate per unit (₹)"])]
                ups = [a for a, _ in rows_]
                ok = (rows_ and ups[-1] is None and all(x is not None for x in ups[:-1])
                      and ups[:-1] == sorted(ups[:-1]) and cat.strip() and src.strip())
                if not ok:
                    st.error("Check slabs (ascending, last row blank), category and source document.")
                else:
                    store.add_tariff(dict(
                        provider_id=next(p["id"] for p in provs if p["name"] == pv), category=cat.strip(),
                        effective_from=str(ef), effective_to=str(et) if has_end else None,
                        slabs=[{"upto": a, "rate": b} for a, b in rows_], fixed_charge=fixed,
                        fixed_prorate_days=prorate, wheeling_per_unit=wh, fac_per_unit=fac, duty_percent=duty,
                        duty_base=base, tax_percent=tax, max_billing_days=mx, source_doc=src.strip(),
                        verified_on=store.today() if ver else None, verified=ver), u["email"])
                    st.success("Saved.")
                    st.rerun()
        st.markdown("#### Tariff history")
        for tr in store.list_tariffs():
            a, b, c = st.columns([6, 2, 2])
            a.markdown(f'<div class="row"><span><b>{tr["provider_name"]}</b> · {tr["category"]} · '
                       f'{tr["effective_from"]} → {tr["effective_to"] or "open"}</span>'
                       f'<span class="pill {"p-ok" if tr["verified"] else "p-warn"}">'
                       f'{"Verified" if tr["verified"] else "Unverified"}</span></div>', unsafe_allow_html=True)
            if tr["verified"]:
                b.button("Un-verify", key=f"uv{tr['id']}", on_click=store.set_tariff_verified,
                         args=(tr["id"], False, None))
            else:
                b.button("Mark verified", key=f"v{tr['id']}", on_click=store.set_tariff_verified,
                         args=(tr["id"], True, store.today()))
            if not tr["effective_to"]:
                c.button("Expire today", key=f"ex{tr['id']}", on_click=store.expire_tariff,
                         args=(tr["id"], store.today()))
    with t[3]:
        errs = store.errors()
        st.dataframe(pd.DataFrame(errs), use_container_width=True, hide_index=True) if errs else st.success("No errors logged.")