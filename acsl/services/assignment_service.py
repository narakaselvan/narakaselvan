from acsl.db import run_query
from acsl.services.hierarchy_service import get_staff_under

def get_assignment_counts(login_user, login_role, workingarea):

    staff = get_staff_under(login_role, workingarea)

    supervisors = [s["login"] for s in staff if s["role"] == "supervisor"]
    interviewers = [s["login"] for s in staff if s["role"] == "interviewer"]

    query = """
        SELECT meta_responsiblename,
               meta_receivedbytabletatutc
        FROM assignments
    """

    rows = run_query(query)

    total = len(rows)
    hold_supervisor = 0
    assigned_interviewer = 0
    received_interviewer = 0

    for r in rows:
        responsible = r["meta_responsiblename"]
        received_time = r["meta_receivedbytabletatutc"]

        if responsible in supervisors:
            hold_supervisor += 1
        elif responsible in interviewers:
            assigned_interviewer += 1
            if received_time:
                received_interviewer += 1

    return total, hold_supervisor, assigned_interviewer, received_interviewer