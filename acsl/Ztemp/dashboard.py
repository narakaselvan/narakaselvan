import streamlit as st
from PIL import Image
import os

# ---------------------------
# Sidebar: Profile Picture
# ---------------------------

st.sidebar.header("User Profile")

# Path to default image (relative to your project)
DEFAULT_IMAGE_PATH = "images/default_profile.jpg"

# File uploader for profile picture
uploaded_file = st.sidebar.file_uploader(
    "Upload profile picture",
    type=["jpg", "jpeg", "png"]
)

# Load image
if uploaded_file is not None:
    try:
        profile_image = Image.open(uploaded_file)
    except Exception as e:
        st.sidebar.error(f"Error opening uploaded image: {e}")
        profile_image = Image.open(DEFAULT_IMAGE_PATH)
else:
    # If no upload, use default
    if os.path.exists(DEFAULT_IMAGE_PATH):
        profile_image = Image.open(DEFAULT_IMAGE_PATH)
    else:
        st.sidebar.error("Default profile image not found!")
        profile_image = None

# Display image if loaded
if profile_image:
    st.sidebar.image(profile_image, width=100)

# ---------------------------
# Additional Sidebar Info
# ---------------------------

st.sidebar.write("Name: Rasiah Kalaichelvan")
st.sidebar.write("Role: Assistant Director of ICT")
st.sidebar.write("Department: Census and Statistics")