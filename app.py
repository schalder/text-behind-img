import streamlit as st
import requests
from rembg import remove
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import os

# Backend URLs
CHECK_SESSION_URL = "https://app.ghlsaaskits.com/text-behind-img/check_session.php"
LOGIN_URL = "https://app.ghlsaaskits.com/text-behind-img/login.php"
LOGOUT_URL = "https://app.ghlsaaskits.com/text-behind-img/logout.php"

# Set up Streamlit page
st.set_page_config(layout="wide", page_title="Image Subject and Text Editor")

# Sidebar upload/download instructions
st.sidebar.write("## Upload and download :gear:")

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB max file size

# Ensure the fonts folder exists
FONTS_FOLDER = "fonts"
if not os.path.exists(FONTS_FOLDER):
    os.makedirs(FONTS_FOLDER)

# Function to convert an image to bytes for download
def convert_image(img, format="PNG"):
    buf = BytesIO()
    img.save(buf, format=format)
    byte_im = buf.getvalue()
    return byte_im

# Function to validate session
def validate_session():
    try:
        response = requests.get(CHECK_SESSION_URL, cookies=requests.utils.dict_from_cookiejar(st.session_state.cookies))
        if response.status_code == 200:
            user_data = response.json()
            st.session_state.user_data = user_data
            return True
        else:
            return False
    except Exception as e:
        st.error("Unable to validate session. Please check your backend configuration.")
        return False

# Initialize session state variables
if "cookies" not in st.session_state:
    st.session_state.cookies = None
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# Validate session or redirect to login
if not validate_session():
    # Redirect to the login page if session validation fails
    st.markdown(
        f"""
        <script>
            window.location.href = "{LOGIN_URL}?redirect_to=https://text-behind-img.streamlit.app/";
        </script>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# Retrieve user data from session state
user_data = st.session_state.user_data

# Display user information and logout button
st.sidebar.markdown(f"**Logged in as:** {user_data['name']} ({user_data['email']})")
if st.sidebar.button("Logout"):
    # Logout the user
    requests.get(LOGOUT_URL, cookies=requests.utils.dict_from_cookiejar(st.session_state.cookies))
    st.session_state.clear()
    # Redirect to login
    st.markdown(
        f"""
        <script>
            window.location.href = "{LOGIN_URL}";
        </script>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# File upload
my_upload = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

st.sidebar.write("### Manage Text Sets")
if "text_sets" not in st.session_state:
    st.session_state.text_sets = [
        {
            "text": "Your Custom Text",
            "font_size": 150,
            "font_color": "#FFFFFF",
            "font_family": "Arial",
            "font_stroke": 2,
            "stroke_color": "#000000",
            "text_opacity": 1.0,
            "rotation": 0,
            "x_position": 0,
            "y_position": 0,
            "text_transform": "none",
        }
    ]

# Render text sets
for i, text_set in enumerate(st.session_state.text_sets):
    with st.sidebar.expander(f"Text Set {i + 1}", expanded=True):
        text_set["text"] = st.text_input(f"Text {i + 1}", text_set["text"], key=f"text_{i}")
        text_set["font_family"] = st.selectbox(
            f"Font Family {i + 1}",
            [f.replace(".ttf", "") for f in os.listdir(FONTS_FOLDER) if f.endswith(".ttf")],
            key=f"font_family_{i}",
        )
        text_set["text_transform"] = st.selectbox(
            f"Text Transform {i + 1}", ["none", "uppercase", "lowercase", "capitalize"], key=f"text_transform_{i}"
        )
        text_set["font_size"] = st.slider(f"Font Size {i + 1}", 10, 400, text_set["font_size"], key=f"font_size_{i}")
        text_set["font_color"] = st.color_picker(f"Font Color {i + 1}", text_set["font_color"], key=f"font_color_{i}")
        text_set["font_stroke"] = st.slider(f"Font Stroke {i + 1}", 0, 10, text_set["font_stroke"], key=f"font_stroke_{i}")
        text_set["stroke_color"] = st.color_picker(f"Stroke Color {i + 1}", text_set["stroke_color"], key=f"stroke_color_{i}")
        text_set["text_opacity"] = st.slider(f"Text Opacity {i + 1}", 0.1, 1.0, text_set["text_opacity"], key=f"text_opacity_{i}")
        text_set["rotation"] = st.slider(f"Rotate Text {i + 1}", 0, 360, text_set["rotation"], key=f"rotation_{i}")
        text_set["x_position"] = st.slider(f"X Position {i + 1}", -400, 400, text_set["x_position"], key=f"x_position_{i}")
        text_set["y_position"] = st.slider(f"Y Position {i + 1}", -400, 400, text_set["y_position"], key=f"y_position_{i}")

# Process uploaded image
if my_upload is not None:
    if my_upload.size > MAX_FILE_SIZE:
        st.error("The uploaded file is too large. Please upload an image smaller than 5MB.")
    else:
        # Processing logic here
        pass
else:
    st.write("Upload an image to begin editing!")
