import streamlit as st

from voltcourt import accounts, auth, store, views
from voltcourt.ui import goto, inject

st.set_page_config(page_title="VoltCourt", page_icon="⚡", layout="wide")
inject()
logged_in = "user" in st.session_state
st.session_state.setdefault("mode", "login")
if not logged_in:
    st.markdown("<style>[data-testid='stSidebar'],[data-testid='collapsedControl']{display:none;}</style>",
                unsafe_allow_html=True)


def set_mode(m):
    st.session_state["mode"] = m


def rules_html(pw, pw2=""):
    h = "".join(f'<div class="rule {"ok" if ok else "no"}">{"✔" if ok else "✖"} {t}</div>'
                for t, ok in auth.password_rules(pw))
    if pw2:
        h += f'<div class="rule {"ok" if pw == pw2 else "no"}">{"✔" if pw == pw2 else "✖"} Passwords match</div>'
    return f'<div class="rules">{h}</div>'


def sign_in(email, name):
    email = email.strip().lower()
    st.session_state.update(user=email, name=name, role=accounts.role(email))


@st.dialog("Sign Up")
def signup_dialog():
    st.caption("It's quick and easy.")
    name = st.text_input("Full name", placeholder="Full name", label_visibility="collapsed", key="r_name")
    email = st.text_input("Gmail", placeholder="Gmail address (name@gmail.com)", label_visibility="collapsed", key="r_email")
    pw = st.text_input("Password", type="password", placeholder="New password", label_visibility="collapsed", key="r_pw")
    pw2 = st.text_input("Confirm", type="password", placeholder="Confirm password", label_visibility="collapsed", key="r_pw2")
    if not pw:
        st.markdown('<div class="hint">Password: 8+ characters, starts with a capital letter, includes one of @ _ #</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(rules_html(pw, pw2), unsafe_allow_html=True)
    if email and not auth.email_ok(email):
        st.markdown('<div class="rule no">✖ Email must end with @gmail.com</div>', unsafe_allow_html=True)
    agree = st.checkbox("I agree to the Terms and Privacy Policy", key="r_agree")
    if st.button("Sign Up", type="primary", use_container_width=True, key="signup_go"):
        if pw != pw2:
            st.error("Passwords do not match.")
        elif not agree:
            st.error("Please accept the Terms and Privacy Policy.")
        else:
            ok, msg, code = auth.register(name, email, pw)
            if ok:
                st.session_state.update(signup_code=code, mode="login")
                st.rerun()
            else:
                st.error(msg)


# ============================ LOGGED OUT ============================
if not logged_in:
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.write("")
        st.write("")
        st.markdown('<div class="logo">⚡ voltcourt</div>'
                    '<div class="tag">Audit your electricity bill and build your case when it is wrong.</div>'
                    '<div class="sub">We recheck units, charges, duty and billing days, then prepare your '
                    'complaint letter.</div>', unsafe_allow_html=True)
    with right:
        mode = st.session_state["mode"]
        with st.container(border=True):
            if mode == "login":
                if "signup_code" in st.session_state:
                    st.success("Account created. Please log in below.")
                    st.markdown("**Save your recovery code (shown once):**")
                    st.code(st.session_state["signup_code"], language=None)
                    if st.button("I have saved it", key="saved_code"):
                        st.session_state.pop("signup_code", None)
                        st.rerun()
                with st.form("login_form", border=False):
                    email = st.text_input("Gmail", placeholder="Gmail address", label_visibility="collapsed",
                                          key="l_email", autocomplete="username")
                    pw = st.text_input("Password", type="password", placeholder="Password",
                                       label_visibility="collapsed", key="l_pw", autocomplete="current-password")
                    submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
                if submitted:
                    name = auth.login(email, pw)
                    if name:
                        sign_in(email, name)
                        st.rerun()
                    else:
                        st.error("Wrong email or password.")
                a, b, c = st.columns([1, 2, 1])
                with b:
                    st.button("Forgotten password?", key="forgot_btn", on_click=set_mode, args=("forgot",),
                              use_container_width=True)
                st.divider()
                a, b, c = st.columns([1, 2, 1])
                with b:
                    if st.button("Create new account", key="create_btn", use_container_width=True):
                        signup_dialog()
            elif mode == "forgot":
                st.markdown("### Reset your password")
                st.caption("Enter your Gmail, your recovery code and a new password.")
                email = st.text_input("Gmail", placeholder="Gmail address", label_visibility="collapsed", key="f_email")
                code = st.text_input("Code", placeholder="Recovery code (XXXX-XXXX-XXXX)", label_visibility="collapsed", key="f_code")
                pw = st.text_input("New", type="password", placeholder="New password", label_visibility="collapsed", key="f_pw")
                pw2 = st.text_input("Confirm", type="password", placeholder="Confirm new password", label_visibility="collapsed", key="f_pw2")
                if pw:
                    st.markdown(rules_html(pw, pw2), unsafe_allow_html=True)
                if st.button("Reset password", type="primary", use_container_width=True, key="reset_go"):
                    if pw != pw2:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg, new_code = auth.reset_password(email, code, pw)
                        if ok:
                            st.session_state.update(reset_code=new_code, mode="reset_done")
                            st.rerun()
                        else:
                            st.error(msg)
                st.divider()
                st.button("← Back to log in", key="back_btn", on_click=set_mode, args=("login",), use_container_width=True)
            else:
                st.markdown("### Password changed ✅")
                st.write("Your old recovery code no longer works. **Save your new recovery code:**")
                st.code(st.session_state.get("reset_code", ""), language=None)
                st.button("Go to log in", type="primary", use_container_width=True, on_click=set_mode,
                          args=("login",), key="done_go")
        st.markdown('<div class="fine">Not legal advice. Your password is salted and hashed.</div>', unsafe_allow_html=True)
    st.stop()

# ============================ LOGGED IN ============================
u = dict(email=st.session_state["user"], name=st.session_state["name"], role=st.session_state.get("role", "user"))
PAGES = {"Dashboard": ("🏠", views.dashboard), "Audit Bill": ("📤", views.audit_page),
         "My Audits": ("🕑", views.my_audits), "Reports": ("📑", views.reports_page),
         "Analytics": ("📈", views.analytics_page), "Explain My Bill": ("💬", views.explain_page),
         "Complaint Letter": ("✉️", views.complaint_page), "Notifications": ("🔔", views.notifications_page),
         "Profile": ("👤", views.profile_page)}
if u["role"] == "admin":
    PAGES["Admin"] = ("🛡️", views.admin_page)
SECTIONS = [("MAIN", ["Dashboard", "Audit Bill", "My Audits", "Reports"]),
            ("INSIGHTS", ["Analytics", "Explain My Bill"]),
            ("TOOLS", ["Complaint Letter", "Notifications"]),
            ("ACCOUNT", ["Profile"] + (["Admin"] if u["role"] == "admin" else []))]

if "_goto" in st.session_state:
    t = st.session_state.pop("_goto")
    t = t if t in PAGES else "Dashboard"
    came_back = st.session_state.pop("_is_back", False)
    cur = st.session_state.get("page", "Dashboard")
    if not came_back and t != cur:
        st.session_state.setdefault("nav_stack", []).append(cur)
        st.session_state["nav_stack"] = st.session_state["nav_stack"][-20:]
    st.session_state["page"] = t
st.session_state.setdefault("page", "Dashboard")
page = st.session_state["page"]
unread = store.unread_count(u["email"])
n_audits = len(store.list_audits(u["email"]))


def _top_search():
    q = st.session_state.get("top_q", "").strip()
    if q:
        st.session_state["hist_q"] = q
        st.session_state["top_q"] = ""
        goto("My Audits")


def _logout():
    for k in list(st.session_state.keys()):
        del st.session_state[k]


with st.sidebar:
    st.markdown('<div class="brand"><div class="bi">⚡</div>VoltCourt</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="profile"><div class="avatar">{u["name"][0].upper()}</div><div>'
                f'<div class="pname">{u["name"]}</div><div class="pmail">{u["email"]}</div></div></div>',
                unsafe_allow_html=True)
    badge = {"My Audits": n_audits, "Notifications": unread}
    for label, names in SECTIONS:
        st.markdown(f'<div class="navsec">{label}</div>', unsafe_allow_html=True)
        for name in names:
            b = f"  ({badge[name]})" if badge.get(name) else ""
            st.button(f"{PAGES[name][0]}  {name}{b}", key=f"nav_{name}", use_container_width=True,
                      type="primary" if name == page else "secondary", on_click=goto, args=(name,))
    st.markdown('<div class="helpcard"><b>Think a bill is wrong?</b>'
                '<p>Run an audit and VoltCourt rechecks every charge.</p></div>', unsafe_allow_html=True)
    st.button("🧾  Start an audit", key="side_audit", on_click=goto, args=("Audit Bill",), use_container_width=True)
    st.divider()
    st.button("↩  Log out", key="logout_btn", on_click=_logout, use_container_width=True)
    st.caption("Not legal advice. Review results before filing a complaint.")

ts, tb, ta = st.columns([6, 1.4, 0.7])
ts.text_input("Search", key="top_q", placeholder="🔍  Search audits by ID or consumer number, then press Enter",
              label_visibility="collapsed", on_change=_top_search)
tb.markdown(f'<div class="chip">🔔 {unread} new</div>', unsafe_allow_html=True)
ta.markdown(f'<div class="avatar sm">{u["name"][0].upper()}</div>', unsafe_allow_html=True)

try:
    PAGES[page][1](u)
except Exception as e:  # logged for the admin Errors tab; the user gets a friendly message
    store.log_error(u["email"], page, repr(e))
    st.error("Something went wrong on this page. The error was logged.")