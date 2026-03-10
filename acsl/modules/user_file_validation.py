import streamlit as st
import re
import pandas as pd


def user_file_validation():

    st.title("Bulk User File Validator")

    # -----------------------------------------------------
    # CONFIGURATION
    # -----------------------------------------------------

    EXPECTED_COLUMNS = [
        "login", "password", "role", "supervisor", "fullname",
        "email", "phonenumber", "workspace", "workingarea", "is_active"
    ]

    VALID_ROLES = [
        "headquarters", "provincial coordinator", "district head", "district coordinator",
        "zonal supervisor", "divisional head", "area supervisor", "supervisor",
        "circle officer", "interviewer"
    ]

    # -----------------------------------------------------
    # FILE UPLOAD
    # -----------------------------------------------------

    file = st.file_uploader(
        "Upload Excel / CSV / TSV File",
        type=["xlsx", "csv", "tsv", "txt"]
    )

    if file is None:
        st.info("Please upload a file to start validation.")
        return

    # -----------------------------------------------------
    # READ FILE
    # -----------------------------------------------------

    try:

        if file.name.endswith(".xlsx"):
            df = pd.read_excel(file)

        elif file.name.endswith(".csv"):
            df = pd.read_csv(file)

        else:
            df = pd.read_csv(file, sep="\t")

    except Exception as e:
        st.error(f"File read error : {e}")
        return

    errors = {}

    # -----------------------------------------------------
    # COLUMN VALIDATION
    # -----------------------------------------------------

    column_errors = []

    missing_cols = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    extra_cols = [c for c in df.columns if c not in EXPECTED_COLUMNS]

    for c in missing_cols:
        column_errors.append(f"Missing column : {c}")

    for c in extra_cols:
        column_errors.append(f"Unexpected column : {c}")

    if column_errors:
        errors["columns"] = column_errors

    # -----------------------------------------------------
    # LOGIN VALIDATION
    # -----------------------------------------------------

    login_errors = []

    if "login" in df.columns:

        if df["login"].isnull().any():
            login_errors.append("Login column contains blank values")

        duplicates = df[df["login"].duplicated()]["login"].tolist()

        if duplicates:
            login_errors.append(f"Duplicate login values : {duplicates}")

    else:
        login_errors.append("Column 'login' missing")

    if login_errors:
        errors["login"] = login_errors

    # -----------------------------------------------------
    # PASSWORD VALIDATION
    # -----------------------------------------------------

    password_errors = []

    if "password" in df.columns:

        for i, val in df["password"].items():

            if pd.isna(val) or val == "":
                password_errors.append(f"Row {i+1} password blank")
                continue

            val_str = str(val)

            pw_err = []

            if not re.search(r"[A-Z]", val_str):
                pw_err.append("missing uppercase letter")

            if not re.search(r"[a-z]", val_str):
                pw_err.append("missing lowercase letter")

            if not re.search(r"\d", val_str):
                pw_err.append("missing number")

            if not re.search(r"[@$!%*?&]", val_str):
                pw_err.append("missing special character")

            if len(val_str) < 8:
                pw_err.append("less than 8 characters")

            if pw_err:
                password_errors.append(
                    f"Row {i+1} password issue: {', '.join(pw_err)}"
                )

    else:
        password_errors.append("Column 'password' missing")

    if password_errors:
        errors["password"] = password_errors

    # -----------------------------------------------------
    # ROLE VALIDATION
    # -----------------------------------------------------

    role_errors = []

    if "role" in df.columns:

        for i, row in df.iterrows():

            role = str(row["role"]).lower()
            login = row["login"] if "login" in df.columns else f"row {i+1}"

            if role not in VALID_ROLES:
                role_errors.append(f"Login '{login}' invalid role '{role}'")

    else:
        role_errors.append("Column 'role' missing")

    if role_errors:
        errors["role"] = role_errors

    # -----------------------------------------------------
    # SUPERVISOR VALIDATION
    # -----------------------------------------------------

    sup_errors = []

    if "supervisor" in df.columns and "login" in df.columns:

        login_set = set(df["login"].astype(str).str.strip())

        for i, row in df.iterrows():

            sup = str(row["supervisor"]).strip()

            if sup not in ["", "nan", "None"] and sup not in login_set:
                sup_errors.append(
                    f"Row {i+1} supervisor '{sup}' not found in login column"
                )

    else:
        sup_errors.append("Column 'supervisor' or 'login' missing")

    if sup_errors:
        errors["supervisor"] = sup_errors

    # -----------------------------------------------------
    # FULLNAME VALIDATION
    # -----------------------------------------------------

    name_errors = []

    if "fullname" in df.columns:

        pattern = re.compile(r"^[A-Za-z\s\.]*$")

        for i, val in df["fullname"].items():

            if pd.notna(val) and not pattern.match(str(val)):
                name_errors.append(f"Row {i+1} invalid fullname '{val}'")

    else:
        name_errors.append("Column 'fullname' missing")

    if name_errors:
        errors["fullname"] = name_errors

    # -----------------------------------------------------
    # EMAIL VALIDATION
    # -----------------------------------------------------

    email_errors = []

    if "email" in df.columns:

        pattern = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

        for i, val in df["email"].items():

            if pd.notna(val) and val != "" and not pattern.match(str(val)):
                email_errors.append(f"Row {i+1} invalid email '{val}'")

    else:
        email_errors.append("Column 'email' missing")

    if email_errors:
        errors["email"] = email_errors

    # -----------------------------------------------------
    # PHONE VALIDATION
    # -----------------------------------------------------

    phone_errors = []

    if "phonenumber" in df.columns:

        pattern = re.compile(r"^0\d{9}$")

        for i, val in df["phonenumber"].items():

            if pd.notna(val) and val != "" and not pattern.match(str(val)):
                phone_errors.append(f"Row {i+1} invalid phone '{val}'")

    else:
        phone_errors.append("Column 'phonenumber' missing")

    if phone_errors:
        errors["phone"] = phone_errors

    # -----------------------------------------------------
    # WORKINGAREA VALIDATION (MULTIPLE AREAS SUPPORTED)
    # -----------------------------------------------------

    wa_errors = []

    if "workingarea" in df.columns:

        pattern = re.compile(r"^[x0-9]{7}$")

        for i, val in df["workingarea"].items():

            val_str = str(val).strip()

            if val_str in ["", "nan", "None"]:
                wa_errors.append(f"Row {i+1} workingarea blank")
                continue

            values = val_str.split(",")

            for v in values:

                v = v.strip()

                if len(v) < 7:
                    v = v.ljust(7, "0")

                if not pattern.match(v):
                    wa_errors.append(
                        f"Row {i+1} invalid workingarea '{v}'"
                    )

    else:
        wa_errors.append("Column 'workingarea' missing")

    if wa_errors:
        errors["workingarea"] = wa_errors

    # -----------------------------------------------------
    # IS_ACTIVE VALIDATION
    # -----------------------------------------------------

    active_errors = []

    if "is_active" in df.columns:

        for i, val in df["is_active"].items():

            if str(val).lower() not in ["true", "false"]:
                active_errors.append(
                    f"Row {i+1} invalid is_active '{val}'"
                )

    else:
        active_errors.append("Column 'is_active' missing")

    if active_errors:
        errors["is_active"] = active_errors

    # -----------------------------------------------------
    # VALIDATION SUMMARY
    # -----------------------------------------------------

    st.subheader("Validation Results")

    if "toggle" not in st.session_state:
        st.session_state.toggle = {}

    def show_result(label, key):

        if key in errors:

            col1, col2 = st.columns([8, 1])

            col1.write(f"{label} : ❌ Fail")

            if col2.button("View", key=f"btn_{key}"):

                st.session_state.toggle[key] = not st.session_state.toggle.get(key, False)

            if st.session_state.toggle.get(key, False):

                with st.expander(f"{label} Errors", expanded=True):

                    for err in errors[key]:
                        st.write(f"• {err}")

        else:
            st.write(f"{label} : ✅ Pass")

    st.write(
        f"The number of columns in the file : {'✅ Pass' if len(df.columns) == 10 else '❌ Fail'}"
    )

    show_result("Map the column headings", "columns")
    show_result("Validating login column values", "login")
    show_result("Validating password column values", "password")
    show_result("Validating Role column values", "role")
    show_result("Validating supervisor column value", "supervisor")
    show_result("Validating fullname column value", "fullname")
    show_result("Validating email column value", "email")
    show_result("Validating phonenumber column value", "phone")
    st.write("Validating workspace column value : ✅ Pass")
    show_result("Validating workingarea values", "workingarea")
    show_result("Validating is_active column value", "is_active")

    # -----------------------------------------------------
    # FINAL RESULT
    # -----------------------------------------------------

    if errors:
        st.warning(
            "Validation completed with errors. Please click 'View' to see details."
        )
    else:
        st.success(
            "All validations passed. File is ready for upload."
        )