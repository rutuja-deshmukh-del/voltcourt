"""Database layer. Adds new tables to the SAME voltcourt.db; existing tables are untouched."""
import json
import sqlite3
from datetime import date
 
from voltcourt import auth
 
SCHEMA = """
create table if not exists providers(
  id integer primary key autoincrement, name text unique, state text);
create table if not exists tariffs(
  id integer primary key autoincrement, provider_id integer, category text,
  effective_from text, effective_to text, slabs text,
  fixed_charge real default 0, fixed_prorate_days integer default 0,
  wheeling_per_unit real default 0, fac_per_unit real default 0,
  duty_percent real default 0, duty_base text default 'all',
  tax_percent real default 0, max_billing_days integer default 0,
  source_doc text, verified_on text, verified integer default 0,
  added_by text, created text default current_timestamp);
create table if not exists connections(
  id integer primary key autoincrement, email text, consumer_no text,
  label text, provider_id integer, category text,
  unique(email, consumer_no));
create table if not exists audit_records(
  id integer primary key autoincrement, email text, connection_id integer,
  consumer_no text, provider_id integer, bill_date text,
  created text default current_timestamp, bill_amount real, calc_amount real,
  overcharge real default 0, status text, issues integer default 0,
  units real, resolution text default 'Pending verification',
  inputs text, result text);
create index if not exists ix_audit_email on audit_records(email, created);
create table if not exists complaints(
  id integer primary key autoincrement, audit_id integer, email text,
  body text, created text default current_timestamp);
create table if not exists notifications(
  id integer primary key autoincrement, email text,
  created text default current_timestamp, kind text, message text,
  is_read integer default 0);
create index if not exists ix_notif_email on notifications(email, is_read);
create table if not exists error_log(
  id integer primary key autoincrement, created text default current_timestamp,
  email text, place text, message text);
"""
 
# Names only. NO tariff rates are ever seeded.
SEED_PROVIDERS = [("MSEDCL (Mahavitaran)", "Maharashtra"), ("BEST", "Maharashtra"),
                  ("Tata Power", "Maharashtra"), ("Adani Electricity", "Maharashtra")]
RESOLUTIONS = ["Pending verification", "Complaint filed",
               "Resolved - bill corrected", "Dismissed - bill was correct"]
 
 
def conn():
    c = auth._conn()
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    if "role" not in [r[1] for r in c.execute("pragma table_info(users)")]:
        c.execute("alter table users add column role text default 'user'")
    for n, s in SEED_PROVIDERS:
        c.execute("insert or ignore into providers(name, state) values(?,?)", (n, s))
    c.commit()
    return c
 
 
def _rows(sql, args=()):
    with conn() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]
 
 
# ---------- providers & tariffs ----------
def providers():
    return _rows("select * from providers order by name")
 
 
def add_provider(name, state):
    with conn() as c:
        c.execute("insert or ignore into providers(name,state) values(?,?)", (name.strip(), state.strip()))
 
 
def add_tariff(t, admin_email):
    with conn() as c:
        c.execute(
            "insert into tariffs(provider_id,category,effective_from,effective_to,slabs,fixed_charge,"
            "fixed_prorate_days,wheeling_per_unit,fac_per_unit,duty_percent,duty_base,tax_percent,"
            "max_billing_days,source_doc,verified_on,verified,added_by) "
            "values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (t["provider_id"], t["category"], t["effective_from"], t.get("effective_to") or None,
             json.dumps(t["slabs"]), t["fixed_charge"], t.get("fixed_prorate_days", 0),
             t["wheeling_per_unit"], t["fac_per_unit"], t["duty_percent"], t["duty_base"],
             t["tax_percent"], t.get("max_billing_days", 0), t["source_doc"],
             t.get("verified_on"), 1 if t.get("verified") else 0, admin_email))
 
 
def list_tariffs():
    rows = _rows("select t.*, p.name as provider_name from tariffs t "
                 "join providers p on p.id=t.provider_id order by p.name, t.category, t.effective_from desc")
    for r in rows:
        r["slabs"] = json.loads(r["slabs"] or "[]")
    return rows
 
 
def set_tariff_verified(tid, verified, on):
    with conn() as c:
        c.execute("update tariffs set verified=?, verified_on=? where id=?",
                  (1 if verified else 0, on if verified else None, tid))
 
 
def expire_tariff(tid, end_date):
    with conn() as c:
        c.execute("update tariffs set effective_to=? where id=?", (end_date, tid))
 
 
def categories():
    return [r["category"] for r in _rows("select distinct category from tariffs where verified=1 order by category")]
 
 
def find_tariff(provider_id, category, bill_date):
    """Only VERIFIED tariffs effective on bill_date are ever used. Returns None otherwise."""
    d = str(bill_date)
    rows = _rows(
        "select t.*, p.name as provider_name from tariffs t join providers p on p.id=t.provider_id "
        "where t.provider_id=? and t.category=? and t.verified=1 and t.effective_from<=? "
        "and (t.effective_to is null or t.effective_to>=?) order by t.effective_from desc limit 1",
        (provider_id, category, d, d))
    if not rows:
        return None
    r = rows[0]
    r["slabs"] = json.loads(r["slabs"] or "[]")
    return r
 
 
# ---------- audits ----------
def save_audit(email, inputs, result, provider_id, connection_id=None):
    with conn() as c:
        cur = c.execute(
            "insert into audit_records(email,connection_id,consumer_no,provider_id,bill_date,bill_amount,"
            "calc_amount,overcharge,status,issues,units,inputs,result) values(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (email, connection_id, inputs["consumer_no"], provider_id, str(inputs["bill_date"]),
             result["billed_total"], result["calc_total"], result["overcharge"], result["status"],
             result["issue_count"], result["units_calc"], json.dumps(inputs, default=str),
             json.dumps(result)))
        return cur.lastrowid
 
 
def list_audits(email):
    return _rows("select a.id,a.consumer_no,a.bill_date,a.created,a.bill_amount,a.calc_amount,"
                 "a.overcharge,a.status,a.issues,a.units,a.resolution,p.name as provider "
                 "from audit_records a left join providers p on p.id=a.provider_id "
                 "where a.email=? order by a.id desc", (email,))
 
 
def get_audit(email, audit_id):
    """Ownership enforced: a user can only read their own audits."""
    rows = _rows("select a.*, p.name as provider from audit_records a "
                 "left join providers p on p.id=a.provider_id where a.id=? and a.email=?",
                 (audit_id, email))
    if not rows:
        return None
    r = rows[0]
    r["inputs"] = json.loads(r["inputs"])
    r["result"] = json.loads(r["result"])
    return r
 
 
def set_resolution(email, audit_id, resolution):
    with conn() as c:
        c.execute("update audit_records set resolution=? where id=? and email=?",
                  (resolution, audit_id, email))
 
 
def avg_units(email, consumer_no):
    r = _rows("select avg(units) as a, count(units) as n from audit_records "
              "where email=? and consumer_no=? and units is not null", (email, consumer_no))[0]
    return r["a"] if r["n"] else None
 
 
# ---------- complaints ----------
def save_complaint(email, audit_id, body):
    with conn() as c:
        c.execute("insert into complaints(audit_id,email,body) values(?,?,?)", (audit_id, email, body))
 
 
def list_complaints(email):
    return _rows("select * from complaints where email=? order by id desc", (email,))
 
 
# ---------- connections ----------
def connections(email):
    return _rows("select c.*, p.name as provider from connections c "
                 "left join providers p on p.id=c.provider_id where c.email=? order by c.id", (email,))
 
 
def add_connection(email, consumer_no, label, provider_id, category):
    try:
        with conn() as c:
            c.execute("insert into connections(email,consumer_no,label,provider_id,category) values(?,?,?,?,?)",
                      (email, consumer_no.strip(), label.strip() or consumer_no.strip(), provider_id, category))
        return True
    except sqlite3.IntegrityError:
        return False
 
 
def delete_connection(email, cid):
    with conn() as c:
        c.execute("delete from connections where id=? and email=?", (cid, email))
 
 
# ---------- notifications ----------
def notify(email, kind, message):
    with conn() as c:
        c.execute("insert into notifications(email,kind,message) values(?,?,?)", (email, kind, message))
 
 
def notifications(email, limit=50):
    return _rows("select * from notifications where email=? order by id desc limit ?", (email, limit))
 
 
def unread_count(email):
    return _rows("select count(*) n from notifications where email=? and is_read=0", (email,))[0]["n"]
 
 
def mark_all_read(email):
    with conn() as c:
        c.execute("update notifications set is_read=1 where email=?", (email,))
 
 
# ---------- monitoring ----------
def log_error(email, place, message):
    try:
        with conn() as c:
            c.execute("insert into error_log(email,place,message) values(?,?,?)", (email, place, str(message)[:500]))
    except Exception:
        pass
 
 
def errors(limit=50):
    return _rows("select * from error_log order by id desc limit ?", (limit,))
 
 
def admin_stats():
    q = lambda s: _rows(s)[0]["n"]
    return {"Users": q("select count(*) n from users"),
            "Audits": q("select count(*) n from audit_records"),
            "Complaints": q("select count(*) n from complaints"),
            "Verified tariffs": q("select count(*) n from tariffs where verified=1"),
            "Unverified tariffs": q("select count(*) n from tariffs where verified=0"),
            "Errors logged": q("select count(*) n from error_log")}
 
 
def today():
    return date.today().isoformat()
 
