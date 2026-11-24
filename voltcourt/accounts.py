"""Roles, profile and change-password. Built on the existing auth module."""
import os

from voltcourt import auth, store


def role(email):
    with store.conn() as c:
        r = c.execute("select role from users where email=?", (email,)).fetchone()
    return (r["role"] if r and r["role"] else "user")


def set_role(email, new_role):
    if new_role not in ("user", "admin"):
        raise ValueError("role must be user or admin")
    with store.conn() as c:
        c.execute("update users set role=? where email=?", (new_role, email.strip().lower()))


def list_users():
    with store.conn() as c:
        return [dict(r) for r in c.execute("select email, name, role, created from users order by created")]


def change_password(email, old, new):
    if auth.login(email, old) is None:
        return False, "Current password is wrong."
    if not all(ok for _, ok in auth.password_rules(new)):
        return False, "New password does not meet all the rules."
    salt = os.urandom(16)
    with store.conn() as c:
        c.execute("update users set salt=?, hash=? where email=?", (salt, auth._hash(new, salt), email))
    return True, "Password changed."