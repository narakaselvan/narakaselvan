import streamlit as st
import bcrypt
from acsl.config import ROLE_HIERARCHY
from acsl.services.user_services import validate_password, normalize_workingarea

def parse_workingarea(area):
    if not area: return {"level": 0}
    area = area.rstrip("0")
    return {
        "level": len(area), 
        "province": area[:1] if len(area) >= 1 else None, 
        "district": area[:2] if len(area) >= 2 else None, 
        "division": area[:4] if len(area) >= 4 else None
    }

def add_user():
    from acsl.db import user_query

    st.subheader("Add New User")

    creator_area = st.session_state.workingarea
    creator_role = st.session_state.role.lower()
    roles_lower = [r.lower() for r in ROLE_HIERARCHY]

    # Handle Admin logic specifically
    if creator_role == "admin":
        next_role = ROLE_HIERARCHY[0] # Admin creates the top level (Headquarters)
    elif creator_role in roles_lower:
        current_index = roles_lower.index(creator_role)
        if current_index == len(ROLE_HIERARCHY) - 1:
            st.warning("You cannot create users below this level")
            return
        next_role = ROLE_HIERARCHY[current_index + 1]
    else:
        st.error(f"Role '{creator_role}' is not authorized to create users.")
        return

    role = st.selectbox("User Role", [next_role])

    # -------------------------------------------------
    # 1. BASIC USER INFO
    # -------------------------------------------------
    login = st.text_input("Login ID")
    password = st.text_input("Password", type="password")
    confirm = st.text_input("Re-enter Password", type="password")
    fullname = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")
    workspace = st.text_input("Workplace")

    # -------------------------------------------------
    # 2. WORKING AREA LOGIC
    # -------------------------------------------------
    st.markdown("### Working Area")
    selected_code = None

    if creator_role == "admin":
        # ADMIN LOGIC: No dropdown needed, forced to Island Level
        st.info("🌍 National Level (0000000) - No selection required for Headquarters users.")
        selected_code = "0000000"

    elif creator_role == "headquarters":
        provinces = user_query("SELECT code,name FROM province ORDER BY name", fetch=True)
        province_dict = {r["name"]: r["code"] for r in provinces}
        options = ["-- Select Province --"] + list(province_dict.keys())
        selected_name = st.selectbox("Select Province", options)
        if selected_name != "-- Select Province --":
            selected_code = province_dict[selected_name]

    else:
        info = parse_workingarea(creator_area)
        level, province, district, division = info["level"], info["province"], info["district"], info["division"]

        if level == 1:
            districts = user_query("SELECT code,name FROM district WHERE LEFT(code,1)=%s ORDER BY name", (province,), fetch=True)
            d_dict = {r["name"]: r["code"] for r in districts}
            options = ["-- Select District --"] + list(d_dict.keys())
            selected_name = st.selectbox("Select District", options)
            if selected_name != "-- Select District --":
                selected_code = d_dict[selected_name]

        elif level == 2:
            divisions = user_query("SELECT code,name FROM division WHERE LEFT(code,2)=%s ORDER BY name", (district,), fetch=True)
            div_dict = {r["name"]: r["code"] for r in divisions}
            options = ["-- Select Division --"] + list(div_dict.keys())
            selected_name = st.selectbox("Select Division", options)
            if selected_name != "-- Select Division --":
                selected_code = div_dict[selected_name]

        elif level == 4:
            gns = user_query("SELECT code,name FROM gndivision WHERE LEFT(code,4)=%s ORDER BY name", (division,), fetch=True)
            gn_dict = {r["name"]: r["code"] for r in gns}
            options = ["-- Select GN Division --"] + list(gn_dict.keys())
            selected_name = st.selectbox("Select GN Division", options)
            if selected_name != "-- Select GN Division --":
                selected_code = gn_dict[selected_name]
        else:
            st.warning("Cannot create users below GN level.")
            return

    # -------------------------------------------------
    # 3. CREATE USER SUBMISSION
    # -------------------------------------------------
    if st.button("Create User", type="primary"):
        if not login:
            st.error("Login ID required")
            return
        if password != confirm:
            st.error("Passwords do not match")
            return
        
        msg = validate_password(password)
        if msg:
            st.error(msg)
            return
            
        if not selected_code:
            st.error("Please select a working area from the dropdown.")
            return
            
        existing = user_query("SELECT login FROM susouser WHERE login=%s", (login,), fetch=True)
        if existing:
            st.error("Login already exists")
            return

        # Hash password for local DB
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        hashed_str = hashed.decode('utf-8')

        # Handle working area format
        workingarea = "0000000" if selected_code == "0000000" else ",".join(normalize_workingarea([selected_code]))

        # --- Local DB Integration ---
        user_query(
            """
            INSERT INTO susouser
            (login,password,role,fullname,email,phonenumber,workspace,workingarea,is_active)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (login, hashed_str, role, fullname, email, phone, workspace, workingarea, True)
        )
        st.success(f"✅ User '{login}' successfully created in local dashboard.")