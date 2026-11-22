import hashlib, hmac, json, os, re, secrets, sqlite3

DB = "voltcourt.db"
GMAIL = re.compile(r"^[a-z0-9._%+-]+@gmail\.com$")
CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _conn():
    c = sqlite3.connect(DB)
    c.execute("create table if not exists users(email text primary key, "
              "name text, salt blob, hash blob, rsalt blob, rhash blob, "
              "created text default current_timestamp)")
    c.execute("create table if not exists audits(id integer primary key "
              "autoincrement, email text, created text default "
              "current_timestamp, consumer_no text, total real, issues int, "
              "overcharge real, data text)")
    return c


def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)


def _new_code():
    groups = ["".join(secrets.choice(CODE_CHARS) for _ in range(4))
              for _ in range(3)]
    return "-".join(groups)


def email_ok(email):
    return bool(GMAIL.match(email.strip().lower()))


def name_ok(name):
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,49}", name.strip()))


def password_rules(pw):
    return [
        ("At least 8 characters", len(pw) >= 8),
        ("Starts with a capital letter (not a number)",
         bool(pw) and pw[0].isalpha() and pw[0].isupper()),
        ("Contains at least one of  @  _  #", any(c in pw for c in "@_#")),
        ("Only letters, numbers and  @ _ #  are used",
         bool(pw) and re.fullmatch(r"[A-Za-z0-9@_#]+", pw) is not None),
    ]


def register(name, email, pw):
    """Returns (ok, message, recovery_code)."""
    email = email.strip().lower()
    if not name_ok(name):
        return False, "Enter your full name (letters only).", None
    if not email_ok(email):
        return False, "Email must be a valid @gmail.com address.", None
    if not all(ok for _, ok in password_rules(pw)):
        return False, "Password does not meet all the rules.", None
    salt, rsalt, code = os.urandom(16), os.urandom(16), _new_code()
    try:
        with _conn() as c:
            c.execute("insert into users(email, name, salt, hash, rsalt, rhash) "
                      "values(?,?,?,?,?,?)",
                      (email, name.strip(), salt, _hash(pw, salt),
                       rsalt, _hash(code, rsalt)))
    except sqlite3.IntegrityError:
        return False, "This email is already registered. Please log in.", None
    return True, "Account created.", code


def login(email, pw):
    with _conn() as c:
        r = c.execute("select name, salt, hash from users where email=?",
                      (email.strip().lower(),)).fetchone()
    if r and hmac.compare_digest(r[2], _hash(pw, r[1])):
        return r[0]
    return None


def reset_password(email, code, new_pw):
    """Returns (ok, message, new_recovery_code)."""
    email = email.strip().lower()
    code = code.strip().upper()
    if not all(ok for _, ok in password_rules(new_pw)):
        return False, "New password does not meet all the rules.", None
    with _conn() as c:
        r = c.execute("select rsalt, rhash from users where email=?",
                      (email,)).fetchone()
        if not r or not hmac.compare_digest(r[1], _hash(code, r[0])):
            return False, "Email or recovery code is incorrect.", None
        salt, rsalt, new_code = os.urandom(16), os.urandom(16), _new_code()
        c.execute("update users set salt=?, hash=?, rsalt=?, rhash=? "
                  "where email=?",
                  (salt, _hash(new_pw, salt), rsalt, _hash(new_code, rsalt),
                   email))
    return True, "Password changed.", new_code


def save_audit(email, bill, issues, overcharge):
    with _conn() as c:
        c.execute("insert into audits(email, consumer_no, total, issues, "
                  "overcharge, data) values(?,?,?,?,?,?)",
                  (email, bill.consumer_no, bill.total_payable, issues,
                   overcharge, json.dumps(bill.__dict__)))


def list_audits(email):
    with _conn() as c:
        return c.execute("select created, consumer_no, total, issues, "
                         "overcharge from audits where email=? "
                         "order by id desc", (email,)).fetchall()
