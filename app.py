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

# Sidebar upload/download instructions
st.sidebar.write("## Upload and download :gear:")

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size

# Ensure the fonts folder exists
FONTS_FOLDER = "fonts"
if not os.path.exists(FONTS_FOLDER):
    os.makedirs(FONTS_FOLDER)

# Function to inject CSS for hiding the sidebar
def hide_sidebar():
    hide_sidebar_css = """
    <style>
        section.stSidebar.st-emotion-cache-1wqrzgl.eczjsme18 {
            display: none;
        }
    </style>
    """
    st.markdown(hide_sidebar_css, unsafe_allow_html=True)

# Redirect user to the login page
def redirect_to_login():
    st.experimental_set_query_params()  # Clear query parameters
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

# Function to validate the user session using the API key
def validate_user():
    query_params = st.experimental_get_query_params()
    api_key = query_params.get("api_key", [None])[0]
    
    if not api_key:
        hide_sidebar()
        st.warning("Click the button below to login")
        redirect_to_login()
    
    response = requests.post(VALIDATE_API_URL, json={"api_key": api_key})
    if response.status_code == 200:
        user_data = response.json()
        return user_data
    else:
        hide_sidebar()
        redirect_to_login()

# Logout functionality
def handle_logout():
    st.experimental_set_query_params()
    hide_sidebar()
    redirect_to_login()

# Validate user session
user_data = validate_user()

# Check user role and remaining usage
if user_data["role"] == "free" and int(user_data["remaining_images"]) <= 0:
    st.error("You have reached your limit of 2 image edits as a free user. Please upgrade your account.")
    st.stop()

# Display user information and logout option
st.sidebar.markdown(f"**Logged in as:** {user_data['name']} ({user_data['email']})")
st.sidebar.write(f"**Role:** {user_data['role'].capitalize()}")
if st.sidebar.button("Logout"):
    handle_logout()

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

# File upload
uploaded_image = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

# Render each text set with collapsible editors
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

# Add buttons for text set management
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

# Process image
if uploaded_image:
    try:
        # Load and process the image
        original_image = Image.open(uploaded_image).convert("RGBA")
        subject_image = remove(original_image)
        
        # Combine the original and subject images
        text_layer = Image.new("RGBA", original_image.size, (255, 255, 255, 0))
        for text_set in st.session_state.text_sets:
            font_path = os.path.join(FONTS_FOLDER, f"{text_set['font_family']}.ttf")
            try:
                font = ImageFont.truetype(font_path, text_set["font_size"])
            except Exception:
                font = ImageFont.load_default()

            draw = ImageDraw.Draw(text_layer)
            r, g, b = tuple(int(text_set["font_color"][i:i+2], 16) for i in (1, 3, 5))
            draw.text(
                (text_set["x_position"] + original_image.width / 2, text_set["y_position"] + original_image.height / 2),
                text_set["text"],
                fill=(r, g, b, int(text_set["text_opacity"] * 255)),
                font=font,
                anchor="mm",
            )

        combined = Image.alpha_composite(original_image, text_layer)
        st.image(combined, caption="Processed Image", use_column_width=True)
        st.sidebar.download_button("Download Image", data=convert_image(combined), file_name="processed_image.png", mime="image/png")

    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.write("Upload an image to begin!")
