import streamlit as st
from acsl.config import ROLE_HIERARCHY
from acsl.services.user_services import validate_password, hash_password, normalize_workingarea

def parse_workingarea(area):
    if not area: return {"level": 0}
    area_stripped = area.rstrip("0")
    return {
        "level": len(area_stripped), 
        "province": area_stripped[:1] if len(area_stripped) >= 1 else None,
        "district": area_stripped[:2] if len(area_stripped) >= 2 else None,
        "division": area_stripped[:4] if len(area_stripped) >= 4 else None
    }

def edit_user():
    from acsl.db import user_query

    st.subheader("Edit User")

    creator_area = st.session_state.workingarea
    creator_role = st.session_state.role.lower()
    roles_lower = [r.lower() for r in ROLE_HIERARCHY]

    # Handle Admin logic specifically
    if creator_role == "admin":
        next_role = ROLE_HIERARCHY[0]
    elif creator_role in roles_lower:
        current_index = roles_lower.index(creator_role)
        if current_index + 1 < len(ROLE_HIERARCHY):
            next_role = ROLE_HIERARCHY[current_index + 1]
        else:
            next_role = None  
    else:
        st.error(f"Role '{creator_role}' is not authorized to edit users.")
        return

    # -----------------------------
    # SEARCH USER
    # -----------------------------
    login_search = st.text_input("Search Login", key="edit_search_login")
    if not login_search:
        return

    user_list = user_query(
        "SELECT * FROM susouser WHERE login=%s",
        (login_search,),
        fetch=True
    )
    if not user_list:
        st.error("User not found")
        return

    user = user_list[0]

    # -----------------------------
    # ROLE CHECK
    # -----------------------------
    if next_role is None or user["role"].lower() != next_role.lower():
        st.error(f"No users found in your scope with editable role '{next_role}'.")
        return

    # -----------------------------
    # WORKING AREA CHECK
    # -----------------------------
    if creator_role not in ["headquarters", "admin"]:
        creator_info = parse_workingarea(creator_area)
        if not user["workingarea"].startswith(creator_area.rstrip("0")[:creator_info["level"]]):
            st.error("User outside your working area")
            return

    # -----------------------------
    # USER DETAILS
    # -----------------------------
    st.markdown("### User Details")
    fullname = st.text_input("Full Name", value=user["fullname"], key="edit_fullname")
    email = st.text_input("Email", value=user["email"], key="edit_email")
    phone = st.text_input("Phone Number", value=user["phonenumber"], key="edit_phone")
    workspace = st.text_input("Workplace", value=user["workspace"], key="edit_workspace")

    # -----------------------------
    # USER STATUS & PASSWORD
    # -----------------------------
    st.markdown("### User Status")
    is_active = st.toggle("Active User", value=bool(user["is_active"]), key="edit_is_active")

    st.markdown("### Change Password (optional)")
    st.info("💡 Note: Changing the password here only updates the local dashboard. The Survey Solutions password must be changed in HQ.")
    password = st.text_input("New Password", type="password", key="edit_password")
    confirm = st.text_input("Re-enter Password", type="password", key="edit_confirm_password")

    # -----------------------------
    # WORKING AREA SELECTION 
    # -----------------------------
    st.markdown("### Working Area")
    st.info(f"Current assigned area code: **{user['workingarea']}**")
    
    selected_code = None

    if creator_role == "admin":
        st.info("🌍 National Level (0000000) - Fixed for Headquarters.")
        selected_code = "0000000"

    elif creator_role == "headquarters":
        provinces = user_query("SELECT code,name FROM province ORDER BY name", fetch=True)
        province_dict = {r["name"]: r["code"] for r in provinces}
        options = ["-- Keep Current Area --"] + list(province_dict.keys())
        selected_name = st.selectbox("Change Province (Optional)", options, key="edit_provinces")
        if selected_name != "-- Keep Current Area --":
            selected_code = province_dict[selected_name]

    else:
        creator_info = parse_workingarea(creator_area)
        level, province, district, division = creator_info["level"], creator_info["province"], creator_info["district"], creator_info["division"]

        if level == 1:
            districts = user_query("SELECT code,name FROM district WHERE LEFT(code,1)=%s ORDER BY name", (province,), fetch=True)
            d_dict = {r["name"]: r["code"] for r in districts}
            options = ["-- Keep Current Area --"] + list(d_dict.keys())
            selected_name = st.selectbox("Change District (Optional)", options, key="edit_districts")
            if selected_name != "-- Keep Current Area --":
                selected_code = d_dict[selected_name]

        elif level == 2:
            divisions = user_query("SELECT code,name FROM division WHERE LEFT(code,2)=%s ORDER BY name", (district,), fetch=True)
            div_dict = {r["name"]: r["code"] for r in divisions}
            options = ["-- Keep Current Area --"] + list(div_dict.keys())
            selected_name = st.selectbox("Change Division (Optional)", options, key="edit_divisions")
            if selected_name != "-- Keep Current Area --":
                selected_code = div_dict[selected_name]

        elif level == 4:
            gns = user_query("SELECT code,name FROM gndivision WHERE LEFT(code,4)=%s ORDER BY name", (division,), fetch=True)
            gn_dict = {r["name"]: r["code"] for r in gns}
            options = ["-- Keep Current Area --"] + list(gn_dict.keys())
            selected_name = st.selectbox("Change GN Division (Optional)", options, key="edit_gns")
            if selected_name != "-- Keep Current Area --":
                selected_code = gn_dict[selected_name]

        else:
            st.warning("You cannot assign working areas below GN level")
            return

    # -----------------------------
    # UPDATE USER
    # -----------------------------
    if st.button("Update User", type="primary"):
        if password:
            if password != confirm:
                st.error("Passwords do not match")
                return
            msg = validate_password(password)
            if msg:
                st.error(msg)
                return
            hashed = hash_password(password)
            user_query("UPDATE susouser SET password=%s WHERE login=%s", (hashed, login_search))

        if selected_code:
            workingarea = "0000000" if selected_code == "0000000" else ",".join(normalize_workingarea([selected_code]))
        else:
            workingarea = user["workingarea"]

        user_query("""
            UPDATE susouser
            SET fullname=%s, email=%s, phonenumber=%s, workspace=%s, workingarea=%s, is_active=%s
            WHERE login=%s
        """, (fullname, email, phone, workspace, workingarea, bool(is_active), login_search))

        st.success("✅ User updated successfully in local dashboard.")