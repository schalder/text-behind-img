import streamlit as st
import requests
from rembg import remove
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import os

# Backend URLs
VALIDATE_API_URL = "https://app.ghlsaaskits.com/text-behind-img/validate_api_key.php"
LOGIN_URL = "https://app.ghlsaaskits.com/text-behind-img/login.php"

# Set up Streamlit page
st.set_page_config(layout="wide", page_title="Image Subject and Text Editor")

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size

# Ensure the fonts folder exists
FONTS_FOLDER = "fonts"
if not os.path.exists(FONTS_FOLDER):
    os.makedirs(FONTS_FOLDER)

# Function to hide the sidebar
def hide_sidebar():
    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"] {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Redirect user to the login page
def redirect_to_login():
    st.experimental_set_query_params()  # Clear query params
    st.session_state.clear()
    st.markdown(f"""
        <h4>You have been logged out. Please log in again.</h4>
        <a href="{LOGIN_URL}" style="text-decoration: none;">
           <button style="
               padding: 10px 20px; 
               background-color: #007bff; 
               color: white; 
               border: none; 
               border-radius: 5px; 
               font-size: 16px; 
               cursor: pointer;">
               Click here to login
           </button>
        </a>
    """, unsafe_allow_html=True)
    st.stop()

# Validate the user session using the API key
def validate_user():
    query_params = st.experimental_get_query_params()
    api_key = query_params.get("api_key", [None])[0]
    
    if not api_key:
        hide_sidebar()
        redirect_to_login()

    response = requests.post(VALIDATE_API_URL, json={"api_key": api_key})
    if response.status_code == 200:
        user_data = response.json()
        return user_data
    else:
        redirect_to_login()

# Logout functionality
def handle_logout():
    st.experimental_set_query_params()
    redirect_to_login()

# Convert image to bytes for download
def convert_image(img, format="PNG"):
    buf = BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()

# Validate user session
user_data = validate_user()

# Initialize text sets in session state
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

# Sidebar user information and controls
st.sidebar.markdown(f"**Logged in as:** {user_data['name']} ({user_data['email']})")
st.sidebar.write(f"**Role:** {user_data['role'].capitalize()}")
if st.sidebar.button("Logout"):
    handle_logout()

# Sidebar: Add or remove text sets
if st.sidebar.button("Add Text Set"):
    st.session_state.text_sets.append({
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
    })

if st.sidebar.button("Remove Last Text Set"):
    if len(st.session_state.text_sets) > 0:
        st.session_state.text_sets.pop()

# Sidebar: Manage each text set
for i, text_set in enumerate(st.session_state.text_sets):
    with st.sidebar.expander(f"Text Set {i + 1}", expanded=True):
        text_set["text"] = st.text_input(f"Text {i + 1}", text_set["text"], key=f"text_{i}")
        text_set["font_family"] = st.selectbox(
            f"Font Family {i + 1}",
            [f.replace(".ttf", "") for f in os.listdir(FONTS_FOLDER) if f.endswith(".ttf")],
            index=[f.replace(".ttf", "") for f in os.listdir(FONTS_FOLDER) if f.endswith(".ttf")].index(text_set["font_family"]),
            key=f"font_family_{i}"
        )
        text_set["font_size"] = st.slider(f"Font Size {i + 1}", 10, 800, text_set["font_size"], key=f"font_size_{i}")
        text_set["font_color"] = st.color_picker(f"Font Color {i + 1}", text_set["font_color"], key=f"font_color_{i}")
        text_set["font_stroke"] = st.slider(f"Font Stroke {i + 1}", 0, 10, text_set["font_stroke"], key=f"font_stroke_{i}")
        text_set["stroke_color"] = st.color_picker(f"Stroke Color {i + 1}", text_set["stroke_color"], key=f"stroke_color_{i}")
        text_set["text_opacity"] = st.slider(f"Text Opacity {i + 1}", 0.1, 1.0, text_set["text_opacity"], step=0.1, key=f"text_opacity_{i}")
        text_set["rotation"] = st.slider(f"Rotate Text {i + 1}", 0, 360, text_set["rotation"], key=f"rotation_{i}")
        text_set["x_position"] = st.slider(f"X Position {i + 1}", -600, 600, text_set["x_position"], key=f"x_position_{i}")
        text_set["y_position"] = st.slider(f"Y Position {i + 1}", -600, 600, text_set["y_position"], key=f"y_position_{i}")

# File upload
uploaded_image = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

# Process and display the image
if uploaded_image:
    original_image = Image.open(uploaded_image).convert("RGBA")
    subject_image = remove(original_image)

    # Combine grayscale background and subject
    grayscale_background = ImageOps.grayscale(original_image).convert("RGBA")
    subject_alpha_mask = subject_image.getchannel("A")
    combined_image = Image.composite(subject_image, grayscale_background, subject_alpha_mask)

    # Create a text overlay layer
    text_layer = Image.new("RGBA", original_image.size, (255, 255, 255, 0))
    for text_set in st.session_state.text_sets:
        font_path = os.path.join(FONTS_FOLDER, f"{text_set['font_family']}.ttf")
        try:
            font = ImageFont.truetype(font_path, text_set["font_size"])
        except Exception:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(text_layer)
        x = original_image.width / 2 + text_set["x_position"]
        y = original_image.height / 2 + text_set["y_position"]
        r, g, b = tuple(int(text_set["font_color"][i:i + 2], 16) for i in (1, 3, 5))
        draw.text((x, y), text_set["text"], fill=(r, g, b, int(255 * text_set["text_opacity"])), font=font)

    final_image = Image.alpha_composite(original_image, text_layer)

    # Display images
    st.image(final_image, caption="Final Image with Text", use_column_width=True)
    st.sidebar.download_button("Download Image", convert_image(final_image), "final_image.png", "image/png")
