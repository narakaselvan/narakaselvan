import streamlit as st
from acsl.config import ROLE_HIERARCHY
from acsl.services.user_services import validate_password, normalize_workingarea
import bcrypt

def parse_workingarea(area):
    if not area:
        return {"level": 0}
    area = area.rstrip("0")
    province = area[:1] if len(area) >= 1 else None
    district = area[:2] if len(area) >= 2 else None
    division = area[:4] if len(area) >= 4 else None
    return {"level": len(area), "province": province, "district": district, "division": division}

def add_user():
    from acsl.db import user_query

    st.subheader("Add New User")

    creator_area = st.session_state.workingarea
    creator_role = st.session_state.role.lower()
    roles_lower = [r.lower() for r in ROLE_HIERARCHY]

    current_index = roles_lower.index(creator_role)
    if current_index == len(ROLE_HIERARCHY) - 1:
        st.warning("You cannot create users below this level")
        return

    next_role = ROLE_HIERARCHY[current_index + 1]
    role = st.selectbox("User Role", [next_role])

    # Basic info
    login = st.text_input("Login ID")
    password = st.text_input("Password", type="password")
    confirm = st.text_input("Re-enter Password", type="password")
    fullname = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")
    workspace = st.text_input("Workplace")

    # Working area
    st.markdown("### Working Area")
    selected_codes = []

    if creator_role == "headquarters":
        provinces = user_query("SELECT code,name FROM province ORDER BY name", fetch=True)
        province_dict = {r["name"]: r["code"] for r in provinces}
        selected_names = st.multiselect("Select Province(s)", list(province_dict.keys()))
        selected_codes = [province_dict[n] for n in selected_names]
    else:
        info = parse_workingarea(creator_area)
        province, district, division, level = info["province"], info["district"], info["division"], info["level"]

        if level == 1:
            districts = user_query("SELECT code,name FROM district WHERE LEFT(code,1)=%s ORDER BY name", (province,), fetch=True)
            d_dict = {r["name"]: r["code"] for r in districts}
            selected_names = st.multiselect("Select District(s)", list(d_dict.keys()))
            selected_codes = [d_dict[n] for n in selected_names]
        elif level == 2:
            divisions = user_query("SELECT code,name FROM division WHERE LEFT(code,2)=%s ORDER BY name", (district,), fetch=True)
            div_dict = {r["name"]: r["code"] for r in divisions}
            selected_names = st.multiselect("Select Division(s)", list(div_dict.keys()))
            selected_codes = [div_dict[n] for n in selected_names]
        elif level == 4:
            gns = user_query("SELECT code,name FROM gndivision WHERE LEFT(code,4)=%s ORDER BY name", (division,), fetch=True)
            gn_dict = {r["name"]: r["code"] for r in gns}
            selected_names = st.multiselect("Select GN Division(s)", list(gn_dict.keys()))
            selected_codes = [gn_dict[n] for n in selected_names]
        else:
            st.warning("Cannot create users below GN level.")
            return

    # Create user
    if st.button("Create User"):
        if password != confirm:
            st.error("Passwords do not match")
            return
        msg = validate_password(password)
        if msg:
            st.error(msg)
            return
        if not login:
            st.error("Login ID required")
            return
        if not selected_codes:
            st.error("Please select at least one working area")
            return
        existing = user_query("SELECT login FROM susouser WHERE login=%s", (login,), fetch=True)
        if existing:
            st.error("Login already exists")
            return

        # Hash password
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        hashed_str = hashed.decode('utf-8')

        workingarea = ",".join(normalize_workingarea(selected_codes))

        # INSERT user with is_active=True
        user_query(
            """
            INSERT INTO susouser
            (login,password,role,fullname,email,phonenumber,workspace,workingarea,is_active)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (login, hashed_str, role, fullname, email, phone, workspace, workingarea, True)
        )
        st.success(f"User '{login}' successfully created.")
