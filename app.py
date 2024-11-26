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
    # Clear query parameters (API key)
    st.experimental_set_query_params()  # Clear any query params

    # Clear the sidebar content
    for key in st.session_state.keys():
        del st.session_state[key]

    # Display the message and redirect button
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

# Function to convert an image to bytes for download
def convert_image(img, format="PNG"):
    buf = BytesIO()
    img.save(buf, format=format)
    byte_im = buf.getvalue()
    return byte_im

# Function to validate the user session using the API key
def validate_user():
    # Extract the API key from the query parameter
    query_params = st.experimental_get_query_params()
    api_key = query_params.get("api_key", [None])[0]
    
    if not api_key:
        hide_sidebar()  # Hide the sidebar if no API key
        st.warning("Click the button below to login")
        redirect_to_login()
        st.stop()
    
    try:
        # Validate API key with the backend
        response = requests.post(VALIDATE_API_URL, json={"api_key": api_key})
        
        if response.status_code == 200:
            user_data = response.json()
            # Ensure all required fields are present
            required_fields = ["user_id", "name", "email", "role", "remaining_images"]
            if not all(field in user_data for field in required_fields):
                st.error("Invalid response from the server. Missing required fields.")
                st.stop()
            return user_data
        elif response.status_code == 401:
            hide_sidebar()  # Hide the sidebar on invalid API key
            st.warning("Invalid or expired API key. Redirecting to login...")
            redirect_to_login()
            st.stop()
        else:
            st.error(f"Unexpected error: {response.text}. Please contact support.")
            st.stop()
    except Exception as e:
        st.error(f"Unable to validate session: {e}. Please try again.")
        st.stop()

# Logout functionality
def handle_logout():
    st.experimental_set_query_params()  # Clear API key from URL
    hide_sidebar()  # Hide the sidebar
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

# Add logout button
if st.sidebar.button("Logout"):
    # Clear all session data
    st.session_state.clear()
    # Redirect to login
    handle_logout()

# Function to create grayscale background while keeping the subject colored
def create_grayscale_with_subject(original_image, subject_image):
    grayscale_background = ImageOps.grayscale(original_image).convert("RGBA")
    subject_alpha_mask = subject_image.getchannel("A")
    combined_image = Image.composite(subject_image, grayscale_background, subject_alpha_mask)
    return combined_image

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
    st.experimental_rerun()  # Reload the page immediately

# File upload
my_upload = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

# Initialize session state for text sets
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
st.sidebar.write("### Manage Text Sets")
for i, text_set in enumerate(st.session_state.text_sets):
    with st.sidebar.expander(f"Text Set {i + 1}", expanded=True):
        if st.button(f"Remove Text Set {i + 1}", key=f"remove_text_set_{i}"):
            remove_text_set(i)
        text_set["text"] = st.text_input(f"Text {i + 1}", text_set["text"], key=f"text_{i}")
        text_set["font_family"] = st.selectbox(
            f"Font Family {i + 1}",
            [f.replace(".ttf", "") for f in os.listdir(FONTS_FOLDER) if f.endswith(".ttf")],
            key=f"font_family_{i}",
        )
        text_set["text_transform"] = st.selectbox(
            f"Text Transform {i + 1}", ["none", "uppercase", "lowercase", "capitalize"], key=f"text_transform_{i}"
        )
        text_set["font_size"] = st.slider(f"Font Size {i + 1}", 10, 800, text_set["font_size"], key=f"font_size_{i}")
        text_set["font_color"] = st.color_picker(f"Font Color {i + 1}", text_set["font_color"], key=f"font_color_{i}")
        text_set["font_stroke"] = st.slider(f"Font Stroke {i + 1}", 0, 10, text_set["font_stroke"], key=f"font_stroke_{i}")
        text_set["stroke_color"] = st.color_picker(f"Stroke Color {i + 1}", text_set["stroke_color"], key=f"stroke_color_{i}")
        text_set["text_opacity"] = st.slider(
            f"Text Opacity {i + 1}", 0.1, 1.0, text_set["text_opacity"], step=0.1, key=f"text_opacity_{i}"
        )
        text_set["rotation"] = st.slider(f"Rotate Text {i + 1}", 0, 360, text_set["rotation"], key=f"rotation_{i}")
        text_set["x_position"] = st.slider(f"X Position {i + 1}", -800, 800, text_set["x_position"], key=f"x_position_{i}")
        text_set["y_position"] = st.slider(f"Y Position {i + 1}", -800, 800, text_set["y_position"], key=f"y_position_{i}")

# Process the uploaded image
if my_upload is not None:
    if my_upload.size > MAX_FILE_SIZE:
        st.error("The uploaded file is too large. Please upload an image smaller than 10MB.")
    else:
        # Process and display the image with text sets
        process_image(my_upload, st.session_state.text_sets)
else:
    st.write("Upload an image to begin editing!")
