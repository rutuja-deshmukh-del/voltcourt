import streamlit as st

PRIMARY, NAVY = "#635bff", "#1e1b6e"
PALETTE = ["#635bff", "#1e1b6e", "#2a7f9e", "#f43f5e", "#22c55e", "#f59e0b", "#8b5cf6"]

CSS = """
<style>
#MainMenu, footer, [data-testid="stToolbar"] {visibility:hidden;}
header[data-testid="stHeader"] {background:transparent;}
[data-testid="InputInstructions"] {display:none !important;}
.stApp {background:#f5f6fa;}
.block-container {padding-top:1.2rem; max-width:1240px;}
h1,h2,h3,h4 {color:#111827 !important; letter-spacing:-.015em;}
html, body, [class*="css"] {font-family:'Inter','Segoe UI',system-ui,sans-serif;}

/* cards */
[data-testid="stVerticalBlockBorderWrapper"] {background:#fff; border:1px solid #eceef5 !important;
  border-radius:18px; box-shadow:0 1px 2px rgba(16,24,40,.04), 0 6px 20px rgba(16,24,40,.04);}

/* inputs */
.stTextInput input,.stNumberInput input,.stDateInput input,.stTextArea textarea,
[data-baseweb="select"]>div {border-radius:12px !important; border:1px solid #e3e6ef !important;
  background:#fff !important; color:#111827 !important; transition:all .2s;}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus {border-color:#635bff !important;
  box-shadow:0 0 0 3px rgba(99,91,255,.16) !important;}

/* buttons */
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button {border-radius:12px; font-weight:600;
  border:1px solid #e3e6ef; background:#fff; color:#1f2937; transition:all .2s;}
.stButton>button:hover,.stDownloadButton>button:hover,.stFormSubmitButton>button:hover {transform:translateY(-2px);
  border-color:#635bff; color:#635bff; box-shadow:0 8px 18px rgba(99,91,255,.16);}
button[data-testid="stBaseButton-primary"],button[data-testid="stBaseButton-primaryFormSubmit"] {
  background:linear-gradient(135deg,#635bff,#8b5cf6) !important; color:#fff !important; border:none !important;}
.st-key-forgot_btn button,.st-key-back_btn button {background:transparent !important; border:none !important;
  color:#635bff !important; box-shadow:none !important;}
.st-key-create_btn button {background:#16a34a !important; color:#fff !important; border:none !important;}

/* sidebar */
[data-testid="stSidebar"] {background:#fff; border-right:1px solid #eceef5;}
[data-testid="stSidebar"] .stButton>button {justify-content:flex-start; text-align:left; padding:.5rem .8rem;
  border-radius:12px; font-weight:500; font-size:.92rem;}
[data-testid="stSidebar"] .stButton>button p {text-align:left; width:100%;}
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {background:transparent; border:none; color:#4b5563;}
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover {background:#f3f4ff; color:#4338ca;
  transform:none; box-shadow:none;}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {background:#eef0ff !important; color:#4338ca !important;
  font-weight:700; box-shadow:inset 3px 0 0 #635bff;}
.brand {display:flex; align-items:center; gap:.6rem; font-size:1.25rem; font-weight:800; color:#111827; margin:.2rem 0 .9rem;}
.brand .bi {width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center;
  background:linear-gradient(135deg,#635bff,#8b5cf6); color:#fff; font-size:1.1rem;}
.navsec {font-size:.68rem; letter-spacing:.09em; color:#9ca3af; font-weight:700; margin:.9rem 0 .25rem .4rem;}
.profile {display:flex; align-items:center; gap:.7rem; padding:.7rem; border-radius:14px; background:#f7f8ff;
  border:1px solid #eceef5; margin-bottom:.4rem; transition:all .25s;} .profile:hover {transform:translateY(-2px); border-color:#c7c9ff;}
.avatar {width:40px; height:40px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-weight:700; color:#fff; background:linear-gradient(135deg,#635bff,#ec4899); flex-shrink:0;}
.avatar.sm {width:38px; height:38px; margin-left:auto;}
.pname {font-weight:600; color:#111827; line-height:1.2;} .pmail {color:#6b7280; font-size:.74rem; word-break:break-all;}
.helpcard {background:linear-gradient(160deg,#eef0ff,#f7f3ff); border-radius:16px; padding:.9rem; margin-top:.8rem;}
.helpcard b {color:#1e1b6e;} .helpcard p {margin:.25rem 0 0; font-size:.78rem; color:#6b7280;}

/* top bar + page header */
.st-key-back_arrow {margin-top:1.1rem;}
.st-key-back_arrow button {width:42px; height:42px; border-radius:50%; padding:0; font-size:1.2rem; background:#fff;
  border:1px solid #e3e6ef; color:#4338ca;}
.st-key-back_arrow button:hover {background:#eef0ff; border-color:#635bff;}
.chip {background:#fff; border:1px solid #eceef5; border-radius:999px; padding:.42rem .9rem; font-weight:600;
  color:#4338ca; text-align:center; white-space:nowrap;}
.ph h1 {font-size:2rem; margin:.4rem 0 .1rem; color:#111827 !important;} .ph p {color:#6b7280; margin:0 0 .6rem;}
.ctitle {font-weight:700; color:#111827; font-size:1.02rem;} .csub {color:#9ca3af; font-size:.8rem; margin-bottom:.4rem;}
.big {font-size:2.1rem; font-weight:800; color:#1e1b6e; letter-spacing:-.02em; line-height:1.1;}

/* KPI */
.kpi {background:#fff; border:1px solid #eceef5; border-radius:18px; padding:1rem 1.1rem; transition:all .25s;
  box-shadow:0 1px 2px rgba(16,24,40,.04); height:100%;}
.kpi:hover {transform:translateY(-4px); box-shadow:0 14px 28px rgba(99,91,255,.14); border-color:#dcdcff;}
.kpi .kh {display:flex; align-items:center; gap:.6rem; margin-bottom:.6rem;}
.kic {width:36px; height:36px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:1.05rem;}
.kpi small {color:#4b5563; font-weight:600; font-size:.85rem;}
.kpi b {display:block; font-size:1.75rem; color:#1e1b6e; letter-spacing:-.02em;}
.kpi .kr {display:flex; align-items:center; gap:.5rem; margin-top:.35rem; font-size:.76rem; color:#6b7280;}
.cg,.cr,.cn {padding:.12rem .55rem; border-radius:999px; font-weight:700; font-size:.74rem;}
.cg {background:#e8f8ee; color:#15803d;} .cr {background:#feecee; color:#be123c;} .cn {background:#eef0ff; color:#4338ca;}

/* lists, rows, pills */
.row {display:flex; justify-content:space-between; align-items:center; gap:.6rem; padding:.65rem .8rem; border-radius:12px;
  background:#fff; border:1px solid #eceef5; margin-bottom:.45rem; transition:all .2s;}
.row:hover {transform:translateX(5px); background:#f7f8ff; border-color:#dcdcff;}
.rav {width:36px; height:36px; border-radius:10px; background:#eef0ff; color:#4338ca; display:flex; align-items:center;
  justify-content:center; font-weight:700; font-size:.8rem; flex-shrink:0;}
.rm {display:flex; align-items:center; gap:.7rem;} .rm small {color:#6b7280; display:block; font-size:.76rem;}
.pill {padding:.14rem .65rem; border-radius:999px; font-size:.72rem; font-weight:700; white-space:nowrap;}
.p-ok {background:#e8f8ee; color:#15803d;} .p-bad {background:#feecee; color:#be123c;}
.p-warn {background:#fff6dd; color:#b45309;} .p-info {background:#e8f0ff; color:#1d4ed8;}
.empty {text-align:center; color:#6b7280; padding:1.6rem 1rem; border:2px dashed #e3e6ef; border-radius:16px;}
.empty .e {font-size:1.9rem;}

/* breakdown bars */
.brow {display:flex; gap:.7rem; align-items:center; margin:.65rem 0;}
.bic {width:38px; height:38px; border-radius:11px; display:flex; align-items:center; justify-content:center; color:#fff; flex-shrink:0;}
.bmid {flex:1;} .bl {display:flex; justify-content:space-between; font-size:.82rem; color:#374151; margin-bottom:.25rem;}
.bl i {color:#9ca3af; font-style:normal; margin-left:.4rem;}
.bbar {height:7px; background:#e8ebf5; border-radius:6px; overflow:hidden;} .bbar div {height:100%; border-radius:6px;}

/* tinted alert blocks */
.alertb {border-radius:14px; padding:.8rem .9rem; margin-bottom:.6rem;}
.alertb .at {font-size:.78rem; color:#374151; font-weight:600;} .alertb .av {font-size:1.05rem; font-weight:800; color:#111827; margin:.1rem 0 .4rem;}
.a-red {background:#fff1f2;} .a-amber {background:#fffbeb;} .a-blue {background:#eff4ff;} .a-green {background:#effbf3;}

/* insight card */
.insight {background:linear-gradient(135deg,#3b37d9,#7c3aed 60%,#ec4899); border-radius:18px; padding:1.1rem 1.2rem;
  color:#fff; min-height:206px; box-shadow:0 14px 30px rgba(99,91,255,.28);}
.insight small {opacity:.85;} .insight .iv {font-size:2.3rem; font-weight:800; letter-spacing:-.02em; margin:.5rem 0 .2rem;}
.insight p {opacity:.9; margin:0; font-size:.9rem;}

/* upload */
.dropicon {width:58px; height:58px; border-radius:50%; background:linear-gradient(135deg,#3b82f6,#06b6d4); color:#fff;
  display:flex; align-items:center; justify-content:center; font-size:1.5rem; margin:.2rem auto .5rem;}
.droptitle {text-align:center; font-weight:800; font-size:1.2rem; color:#111827;}
.dropsub {text-align:center; color:#6b7280; font-size:.88rem; margin-bottom:.6rem;}
[data-testid="stFileUploaderDropzone"] {background:#eaf3ff !important; border:2px solid #4da3ff !important;
  border-radius:18px !important; padding:1.4rem !important;}
.hl {text-align:center; color:#9ca3af; font-size:.72rem; letter-spacing:.1em; font-weight:700; margin:1.1rem 0 .6rem;}
.fc {background:#fff; border:1px solid #eceef5; border-radius:14px; padding:.8rem 1rem; display:flex; gap:.7rem; height:100%;}
.fc .fi {width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center; flex-shrink:0;}
.fc b {display:block; font-size:.9rem;} .fc span {color:#6b7280; font-size:.78rem;}
.fmt {display:inline-block; background:#1d9bf0; color:#fff; border-radius:999px; padding:.15rem .7rem; font-size:.72rem;
  font-weight:700; margin:0 .15rem;}

/* stepper */
.steps {display:flex; gap:.6rem; margin-bottom:1rem;}
.step {flex:1; background:#fff; border:1px solid #eceef5; border-radius:14px; padding:.6rem .9rem; color:#6b7280; font-size:.88rem;}
.step b {display:inline-flex; width:24px; height:24px; border-radius:50%; background:#eceef5; color:#4b5563;
  align-items:center; justify-content:center; margin-right:.5rem; font-size:.8rem;}
.step.active {border-color:#635bff; color:#4338ca; background:#f4f3ff;} .step.active b {background:#635bff; color:#fff;}
.step.done b {background:#16a34a; color:#fff;}

/* report banner */
.meta {display:flex; gap:2rem; flex-wrap:wrap; font-size:.82rem; color:#6b7280; margin:.2rem 0 .8rem;}
.meta b {display:block; color:#111827; font-size:.88rem;}
.vbanner {border-radius:16px; padding:1.3rem 1.4rem; border:1px solid; height:100%;}
.vbanner h2 {margin:0; font-size:1.7rem; letter-spacing:.01em;} .vbanner p {margin:.4rem 0 0; color:#374151;}
.vbanner.ok {background:#f0fdf4; border-color:#bbf7d0;} .vbanner.ok h2 {color:#15803d !important;}
.vbanner.bad {background:#fff1f2; border-color:#fecdd3;} .vbanner.bad h2 {color:#be123c !important;}
.vbanner.warn {background:#fffbeb; border-color:#fde68a;} .vbanner.warn h2 {color:#b45309 !important;}
.vbanner.info {background:#eff6ff; border-color:#bfdbfe;} .vbanner.info h2 {color:#1d4ed8 !important;}
.scorebox {padding:.4rem .5rem;} .scorebox .sv {font-size:2.3rem; font-weight:800; color:#111827;}
.sbar {height:8px; background:#e8ebf5; border-radius:6px; overflow:hidden; margin:.4rem 0 .7rem;} .sbar div {height:100%; border-radius:6px;}
.sstat {display:flex; justify-content:space-between; font-size:.84rem; color:#4b5563; padding:.15rem 0;}
.mini {background:#fff; border:1px solid #eceef5; border-radius:14px; padding:.7rem .9rem; margin-bottom:.5rem;}
.mini .mt {display:inline-block; font-size:.7rem; font-weight:700; padding:.1rem .55rem; border-radius:8px; margin-bottom:.3rem;}
.mini b {display:block; font-size:.9rem;} .mini small {color:#6b7280;}
.t-pass {background:#e8f8ee; color:#15803d;} .t-fail {background:#feecee; color:#be123c;} .t-skip {background:#eef0f5; color:#6b7280;}
.chk {display:flex; gap:.6rem; align-items:flex-start; padding:.5rem .7rem; border-radius:12px; background:#fff;
  border:1px solid #eceef5; margin-bottom:.4rem;} .chk small {color:#6b7280;}
.chk .ci {font-weight:700;} .chk.pass .ci {color:#16a34a;} .chk.fail .ci {color:#dc2626;} .chk.skip .ci {color:#9ca3af;}
.chk.fail {border-color:#fecdd3; background:#fff7f8;}
.fcard {background:#fff; border:1px solid #eceef5; border-left:5px solid #f97316; border-radius:14px;
  padding:.9rem 1.1rem; margin-bottom:.7rem; transition:all .2s;} .fcard:hover {transform:translateX(5px);}
.fcard.bad {border-left-color:#e11d48;} .fcard.warn {border-left-color:#eab308;} .fcard.info {border-left-color:#3b82f6;}
.fcard .ft {display:flex; justify-content:space-between; font-weight:700; margin-bottom:.4rem;}
.fgrid {display:grid; grid-template-columns:repeat(3,1fr); gap:.5rem; margin:.4rem 0;}
.fgrid div {background:#f8f9fc; border-radius:10px; padding:.4rem .6rem;} .fgrid small {color:#6b7280; display:block;}
.fcard p {margin:.25rem 0; font-size:.88rem; color:#374151;}
.live {font-size:.88rem; padding:.3rem 0;} .live.ok {color:#15803d;} .live.no {color:#b45309;}

/* login */
.logo {font-size:3.2rem; font-weight:800; color:#635bff; letter-spacing:-.03em; line-height:1;}
.tag {font-size:1.5rem; color:#111827; margin-top:.8rem; max-width:460px; line-height:1.3;}
.sub {color:#6b7280; margin-top:.8rem; max-width:440px;}
.rules {background:#f7f8fa; border-radius:10px; padding:.5rem .8rem; margin-bottom:.6rem;}
.rule {font-size:.84rem; padding:.08rem 0;} .rule.ok {color:#16a34a;} .rule.no {color:#dc2626;}
.hint {color:#6b7280; font-size:.82rem; margin:-.2rem 0 .5rem;}
.fine {color:#6b7280; font-size:.78rem; text-align:center; margin-top:.6rem;}
</style>
"""

PILL = {"No Discrepancy Found": "p-ok", "Calculation Error": "p-bad", "Potential Billing Discrepancy": "p-bad",
        "Tariff Verification Required": "p-warn", "Manual Review Required": "p-warn",
        "Missing Information": "p-info"}


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def rupees(x):
    return "n/a" if x is None else f"₹{x:,.2f}"


def mask(n):
    n = str(n or "")
    return "•" * max(0, len(n) - 3) + n[-3:]


def kpi(label, value, color=PRIMARY, sub="", icon="", delta=""):
    ic = f'<span class="kic" style="background:{color}1f;color:{color}">{icon}</span>' if icon else ""
    row = f'<div class="kr">{delta}<span>{sub}</span></div>' if (delta or sub) else ""
    return f'<div class="kpi"><div class="kh">{ic}<small>{label}</small></div><b>{value}</b>{row}</div>'


def chip(text, kind="n"):
    return f'<span class="c{kind}">{text}</span>'


def ctitle(title, sub=""):
    st.markdown(f'<div class="ctitle">{title}</div><div class="csub">{sub}</div>', unsafe_allow_html=True)


def pill(status):
    return f'<span class="pill {PILL.get(status, "p-info")}">{status}</span>'


def empty(icon, title, text):
    st.markdown(f'<div class="empty"><div class="e">{icon}</div><b>{title}</b><br>{text}</div>',
                unsafe_allow_html=True)


def goto(page, **state):
    """Use as on_click=goto, args=(page,) or call directly before st.rerun()."""
    st.session_state.update(state)
    st.session_state["_goto"] = page


def go_back():
    """Return to the previous page (browser Back does not work inside Streamlit)."""
    stack = st.session_state.get("nav_stack", [])
    if stack:
        st.session_state["_is_back"] = True
        st.session_state["_goto"] = stack.pop()


def header(title, sub="", action=None):
    """Page title like a modern SaaS app, with a back arrow once you have navigated somewhere.
    action=(label, page) adds a button on the right."""
    has_back = bool(st.session_state.get("nav_stack"))
    widths = ([0.55] if has_back else []) + [5, 1.3 if action else 0.01]
    cols = st.columns(widths)
    i = 0
    if has_back:
        cols[0].button("←", key="back_arrow", on_click=go_back, help="Back to the previous page")
        i = 1
    cols[i].markdown(f'<div class="ph"><h1>{title}</h1><p>{sub}</p></div>', unsafe_allow_html=True)
    if action:
        cols[i + 1].write("")
        cols[i + 1].button(action[0], on_click=goto, args=(action[1],), type="primary",
                           use_container_width=True, key=f"hdr_{action[1]}")