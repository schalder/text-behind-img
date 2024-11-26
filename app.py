import streamlit as st
from rembg import remove
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import requests
import os

# Backend URLs
CHECK_SESSION_URL = "https://app.ghlsaaskits.com/text-behind-img/check_session.php"
LOGIN_URL = "https://app.ghlsaaskits.com/text-behind-img/login.php"
LOGOUT_URL = "https://app.ghlsaaskits.com/text-behind-img/logout.php"

# Set up Streamlit page
st.set_page_config(layout="wide", page_title="Image Subject and Text Editor")

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

# Redirect non-logged-in users to the PHP login page
if "cookies" not in st.session_state:
    st.session_state.cookies = requests.cookies.RequestsCookieJar()
if "user_data" not in st.session_state:
    st.session_state.user_data = None

if not validate_session():
    # Redirect to PHP login page
    st.markdown(
        f"""
        <script>
            window.location.href = "{LOGIN_URL}?redirect_to=https://text-behind-img.streamlit.app/";
        </script>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# Retrieve user data
user_data = st.session_state.user_data

# Display top navigation with user info and logout
st.markdown(
    f"""
    <style>
        .topnav {{
            background-color: #333;
            overflow: hidden;
            color: white;
            font-size: 18px;
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .topnav a {{
            color: white;
            text-decoration: none;
            margin-left: 20px;
        }}
    </style>
    <div class="topnav">
        <div>Welcome, {user_data['name']} ({user_data['role']})</div>
        <a href="{LOGOUT_URL}">Logout</a>
    </div>
    """,
    unsafe_allow_html=True,
)

# Role-based restrictions
if user_data["role"] == "free":
    st.warning("You are on a Free plan. You can generate and download only 2 images.")
    remaining_images = int(user_data.get("remaining_images", 0))
    if remaining_images <= 0:
        st.error("You have reached your limit for generating images. Upgrade to Pro for unlimited access!")
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

# Function to handle adding a new text set
def add_text_set():
    st.session_state.text_sets.append(
        {
            "text": "New Text",
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
    )

# Function to handle removing a text set
def remove_text_set(index):
    st.session_state.text_sets.pop(index)

# Button to add a new text set
st.sidebar.button("Add Text Set", on_click=add_text_set)

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
        text_set["font_size"] = st.slider(f"Font Size {i + 1}", 10, 400, text_set["font_size"], key=f"text_size_{i}")
        text_set["font_color"] = st.color_picker(f"Font Color {i + 1}", text_set["font_color"], key=f"text_color_{i}")
        text_set["font_stroke"] = st.slider(f"Font Stroke {i + 1}", 0, 10, text_set["font_stroke"], key=f"text_stroke_{i}")
        text_set["stroke_color"] = st.color_picker(f"Stroke Color {i + 1}", text_set["stroke_color"], key=f"stroke_color_{i}")
        text_set["text_opacity"] = st.slider(f"Text Opacity {i + 1}", 0.1, 1.0, text_set["text_opacity"], key=f"text_opacity_{i}")
        text_set["rotation"] = st.slider(f"Rotate Text {i + 1}", 0, 360, text_set["rotation"], key=f"rotation_{i}")
        text_set["x_position"] = st.slider(f"X Position {i + 1}", -400, 400, text_set["x_position"], key=f"x_position_{i}")
        text_set["y_position"] = st.slider(f"Y Position {i + 1}", -400, 400, text_set["y_position"], key=f"y_position_{i}")

# Process uploaded image
if my_upload is not None:
    if user_data["role"] == "free":
        if remaining_images <= 0:
            st.error("You have reached your limit for generating images. Upgrade to Pro for unlimited access!")
            st.stop()

    if my_upload.size > MAX_FILE_SIZE:
        st.error("The uploaded file is too large. Please upload an image smaller than 5MB.")
    else:
        st.success("Image uploaded successfully. Processing logic goes here.")
else:
    st.write("Upload an image to begin editing!")
