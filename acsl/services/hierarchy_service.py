from acsl.db import run_query
from acsl.config import ROLE_HIERARCHY

def get_staff_under(login_role, workingarea):

    login_role = login_role.lower()

    login_role = login_role.strip().lower()

    roles_lower = [r.lower() for r in ROLE_HIERARCHY]

    if login_role not in roles_lower:
        return []   # circle officer or unknown role → no staff under them

    role_index = roles_lower.index(login_role)


    lower_roles = ROLE_HIERARCHY[role_index + 1:]

    if not lower_roles:
        return []

    query = """
        SELECT login, role, workingarea
        FROM susouser
        WHERE role = ANY(%s)
    """

    params = [lower_roles]

    rows = run_query(query, tuple(params))

    for r in rows:
        r["role"] = r["role"].lower()

    return rows