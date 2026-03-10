import streamlit as st
from acsl.config import ROLE_HIERARCHY
from acsl.services.user_services import validate_password, hash_password, normalize_workingarea

def parse_workingarea(area):
    """
    Remove trailing zeros and determine hierarchy level
    """
    if not area:
        return {"level": 0}

    area_stripped = area.rstrip("0")
    return {
        "level": len(area_stripped),  # 1=Province, 2=District, 4=Division, 7=GN
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
    current_index = roles_lower.index(creator_role)

    # Determine the next editable role only
    if current_index + 1 < len(ROLE_HIERARCHY):
        next_role = ROLE_HIERARCHY[current_index + 1]
    else:
        next_role = None  # No role below current

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
    # NEXT LEVEL ROLE CHECK
    # -----------------------------
    if next_role is None or user["role"].lower() != next_role.lower():
        st.error(f"No users found in your working area with editable role '{next_role}'.")
        return

    # -----------------------------
    # WORKING AREA CHECK
    # -----------------------------
    if creator_role != "headquarters":
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
    # USER STATUS
    # -----------------------------
    st.markdown("### User Status")
    is_active = st.toggle("Active User", value=bool(user["is_active"]), key="edit_is_active")

    # -----------------------------
    # PASSWORD CHANGE
    # -----------------------------
    st.markdown("### Change Password (optional)")
    password = st.text_input("New Password", type="password", key="edit_password")
    confirm = st.text_input("Re-enter Password", type="password", key="edit_confirm_password")

    # -----------------------------
    # WORKING AREA SELECTION (Next Level Only)
    # -----------------------------
    st.markdown("### Working Area")
    selected_codes = []

    if creator_role == "headquarters":
        # HQ selects provinces
        provinces = user_query("SELECT code,name FROM province ORDER BY name", fetch=True)
        province_dict = {r["name"]: r["code"] for r in provinces}
        selected_names = st.multiselect("Select Province(s)", list(province_dict.keys()), key="edit_provinces")
        selected_codes = [province_dict[n] for n in selected_names]
    else:
        creator_info = parse_workingarea(creator_area)
        level = creator_info["level"]
        province = creator_info["province"]
        district = creator_info["district"]
        division = creator_info["division"]

        # Province level -> select districts
        if level == 1:
            districts = user_query(
                "SELECT code,name FROM district WHERE LEFT(code,1)=%s ORDER BY name",
                (province,),
                fetch=True
            )
            district_dict = {r["name"]: r["code"] for r in districts}
            selected_names = st.multiselect("Select District(s)", list(district_dict.keys()), key="edit_districts")
            selected_codes = [district_dict[n] for n in selected_names]

        # District level -> select divisions
        elif level == 2:
            divisions = user_query(
                "SELECT code,name FROM division WHERE LEFT(code,2)=%s ORDER BY name",
                (district,),
                fetch=True
            )
            division_dict = {r["name"]: r["code"] for r in divisions}
            selected_names = st.multiselect("Select Division(s)", list(division_dict.keys()), key="edit_divisions")
            selected_codes = [division_dict[n] for n in selected_names]

        # Division level -> select GN divisions
        elif level == 4:
            gns = user_query(
                "SELECT code,name FROM gndivision WHERE LEFT(code,4)=%s ORDER BY name",
                (division,),
                fetch=True
            )
            gn_dict = {r["name"]: r["code"] for r in gns}
            selected_names = st.multiselect("Select GN Division(s)", list(gn_dict.keys()), key="edit_gns")
            selected_codes = [gn_dict[n] for n in selected_names]

        else:
            st.warning("You cannot assign working areas below GN level")
            return

    # -----------------------------
    # UPDATE USER
    # -----------------------------
    if st.button("Update User"):

        # Update password if provided
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

        # Update working area
        if selected_codes:
            normalized_codes = normalize_workingarea(selected_codes)
            workingarea = ",".join(normalized_codes)
        else:
            workingarea = user["workingarea"]

        # Update all details
        user_query("""
            UPDATE susouser
            SET fullname=%s,
                email=%s,
                phonenumber=%s,
                workspace=%s,
                workingarea=%s,
                is_active=%s
            WHERE login=%s
        """, (
            fullname,
            email,
            phone,
            workspace,
            workingarea,
            bool(is_active),  # PostgreSQL boolean
            login_search
        ))

        st.success("User updated successfully")