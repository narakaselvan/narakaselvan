import streamlit as st
import pandas as pd
import os

def prepare_assignments():

    st.title("F3 Assignment File Generator")

    # -------------------------------------------------
    # Create assignments directory
    # -------------------------------------------------
    ASSIGN_DIR = "assignments"
    if not os.path.exists(ASSIGN_DIR):
        os.makedirs(ASSIGN_DIR)

    # -------------------------------------------------
    # Load file
    # -------------------------------------------------
    def load_file(file):
        name = file.name.lower()
        if name.endswith(".xlsx"):
            return pd.read_excel(file)
        elif name.endswith(".csv"):
            return pd.read_csv(file)
        else:
            return pd.read_csv(file, sep="\t")

    # -------------------------------------------------
    # Upload files
    # -------------------------------------------------
    f3_file = st.file_uploader("Upload F3 List", type=["xlsx", "csv"])
    user_file = st.file_uploader("Upload Supervisor/User File", type=["xlsx", "csv", "txt", "tab"])

    if f3_file and user_file:

        f3 = load_file(f3_file)
        users = load_file(user_file)

        st.subheader("F3 Preview")
        st.dataframe(f3.head())

        st.subheader("User File Preview")
        st.dataframe(users.head())

        # -------------------------------------------------
        # Required columns
        # -------------------------------------------------
        required_f3 = [
            "A_15SNO","A0_MRCB_NUMBER","A0.1_MRCB_LETTER",
            "A1_DISTRICT_NAME","A1_DISTRICT_CODE",
            "A2_DS_NAME","A2_DS_CODE",
            "A3_GN_NAME","A3_GN_CODE",
            "A10_CENSUS_BLOCK_NUMBER",
            "A11A_BUILDING_NUMBER","A11B_BUILDING_NUMBER_LETTER",
            "A12A_UNIT_NUMBER","A12B_UNIT_NUMBER_LETTER",
            "A13_UNIT_TYPE","A16_HOUSEHOLD_NO",
            "HOUSEHOLD HEAD NAME/PERSON INCHARGE/OWNER",
            "ADDRESS"
        ]

        missing = [c for c in required_f3 if c not in f3.columns]
        if missing:
            st.error(f"Missing columns in F3 file: {missing}")
            st.stop()

        # -------------------------------------------------
        # Replace NULL A0.1_MRCB_LETTER with '0'
        # -------------------------------------------------
        f3["A0.1_MRCB_LETTER"] = f3["A0.1_MRCB_LETTER"].fillna("0").replace("", "0")

        # -------------------------------------------------
        # Duplicate check
        # -------------------------------------------------
        dup = f3.duplicated()
        if dup.sum() > 0:
            st.warning(f"{dup.sum()} duplicate rows found")

        # -------------------------------------------------
        # Format codes
        # -------------------------------------------------
        f3["A1b"] = f3["A1_DISTRICT_CODE"].astype(int).apply(lambda x: f"{x:02d}")
        f3["A2b"] = f3["A2_DS_CODE"].astype(int).apply(lambda x: f"{x:02d}")
        f3["A3b"] = f3["A3_GN_CODE"].astype(int).apply(lambda x: f"{x:03d}")

        users["DST_CODE"] = users["DST_CODE"].astype(int).apply(lambda x: f"{x:02d}")
        users["DIV_CODE"] = users["DIV_CODE"].astype(int).apply(lambda x: f"{x:02d}")

        # -------------------------------------------------
        # Create BLOCK_ID
        # -------------------------------------------------
        f3["BLOCK_ID"] = f3["A0_MRCB_NUMBER"].astype(str) + f3["A0.1_MRCB_LETTER"].astype(str)

        # -------------------------------------------------
        # Build assignment dataframe
        # -------------------------------------------------
        df = pd.DataFrame()

        df["B7"] = f3["HOUSEHOLD HEAD NAME/PERSON INCHARGE/OWNER"]
        df["B8"] = f3["ADDRESS"]
        df["A15"] = f3["A_15SNO"]
        df["A0"] = f3["A0_MRCB_NUMBER"]
        df["A01"] = f3["A0.1_MRCB_LETTER"]

        df["A1a"] = f3["A1_DISTRICT_NAME"]
        df["A1b"] = f3["A1b"]

        df["A2a"] = f3["A2_DS_NAME"]
        df["A2b"] = f3["A2b"]

        df["A3a"] = f3["A3_GN_NAME"]
        df["A3b"] = f3["A3b"]

        df["A10"] = f3["A10_CENSUS_BLOCK_NUMBER"]

        df["A11a"] = f3["A11A_BUILDING_NUMBER"]
        df["A11b"] = f3["A11B_BUILDING_NUMBER_LETTER"]

        df["A12a"] = f3["A12A_UNIT_NUMBER"]
        df["A12b"] = f3["A12B_UNIT_NUMBER_LETTER"]

        df["A13"] = f3["A13_UNIT_TYPE"]
        df["A14a"] = f3["A16_HOUSEHOLD_NO"]

        df["_quantity"] = 1

        # -------------------------------------------------
        # Merge with users
        # -------------------------------------------------
        df = df.merge(
            users[["DST_CODE","DIV_CODE","login"]],
            left_on=["A1b","A2b"],
            right_on=["DST_CODE","DIV_CODE"],
            how="left"
        )

        df["_responsible"] = df["login"]
        df["BLOCK_ID"] = f3["BLOCK_ID"]

        # -------------------------------------------------
        # Generate button
        # -------------------------------------------------
        if st.button("Generate Assignment Files"):

            rows = []

            for block, group in df.groupby("BLOCK_ID"):

                rows.append(group)

                last = group.iloc[-1].copy()
                last["_quantity"] = -1

                blank_cols = ["B7","B8","A15","A10","A11a","A11b","A12a","A12b","A13","A14a"]

                for col in blank_cols:
                    last[col] = ""

                rows.append(pd.DataFrame([last]))

            df_final = pd.concat(rows).reset_index(drop=True)

            df_final = df_final.drop(columns=["login","DST_CODE","DIV_CODE","BLOCK_ID"], errors="ignore")

            # -------------------------------------------------
            # Fix column order
            # -------------------------------------------------
            cols = list(df_final.columns)

            if "_responsible" in cols and "_quantity" in cols:
                cols.remove("_quantity")
                resp_index = cols.index("_responsible")
                cols.insert(resp_index + 1, "_quantity")

            df_final = df_final[cols]

            # -------------------------------------------------
            # Generate files
            # -------------------------------------------------
            progress = []

            for (district, division), g in df_final.groupby(["A1b","A2b"]):

                division_name = str(g["A2a"].iloc[0]).replace(" ","_")

                filename = f"{district}{division}_{division_name}.txt"

                filepath = os.path.join(ASSIGN_DIR, filename)

                g.to_csv(filepath, sep="\t", index=False, encoding="utf-8")

                blocks = (g["A0"].astype(str) + g["A01"].astype(str)).nunique()
                assignments = (g["_quantity"] == 1).sum()
                unlimited = (g["_quantity"] == -1).sum()

                progress.append({
                    "filename": filename,
                    "districtcode": district,
                    "divisioncode": division,
                    "noofblocks": blocks,
                    "noofassignments": assignments,
                    "noofunlimitedassignments": unlimited
                })

            progress_df = pd.DataFrame(progress)

            # -------------------------------------------------
            # Add total row
            # -------------------------------------------------
            total_row = {
                "filename":"TOTAL",
                "districtcode":"",
                "divisioncode":"",
                "noofblocks":progress_df["noofblocks"].sum(),
                "noofassignments":progress_df["noofassignments"].sum(),
                "noofunlimitedassignments":progress_df["noofunlimitedassignments"].sum()
            }

            progress_df = pd.concat([progress_df,pd.DataFrame([total_row])],ignore_index=True)

            st.subheader("Progress Report")
            st.dataframe(progress_df, use_container_width=True)

            st.success(f"Files saved in folder: {ASSIGN_DIR}")