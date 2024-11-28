import streamlit as st
import requests
from rembg import remove
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import os

# Backend URLs
VALIDATE_API_URL = "https://app.ghlsaaskits.com/text-behind-img/validate_api_key.php"
LOGIN_URL = "https://app.ghlsaaskits.com/text-behind-img/login.php"
UPGRADE_URL = "https://ghlsaaskits.com/upgrade-tbi"

# Set up Streamlit page
st.set_page_config(layout="wide", page_title="Image Subject and Text Editor")

# Sidebar upload/download instructions
st.sidebar.write("## Upload and download :gear:")

MAX_FILE_SIZE = 7 * 1024 * 1024  # 10MB max file size

# Ensure the fonts folder exists
FONTS_FOLDER = "fonts"
if not os.path.exists(FONTS_FOLDER):
    os.makedirs(FONTS_FOLDER)

# Load available fonts
available_fonts = [f.replace(".ttf", "") for f in os.listdir(FONTS_FOLDER) if f.endswith(".ttf")]

# Ensure "Arial Black" is in the available fonts list
if "Arial Black" not in available_fonts:
    st.warning("Arial Black font is not available in the uploaded fonts folder. Please upload it to the 'fonts' folder.")

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
    st.experimental_set_query_params()  # Clear any query params
    for key in st.session_state.keys():
        del st.session_state[key]

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
    return buf.getvalue()

# Function to validate the user session using the API key
def validate_user():
    query_params = st.experimental_get_query_params()
    api_key = query_params.get("api_key", [None])[0]
    if not api_key:
        hide_sidebar()
        st.warning("Click the button below to login")
        redirect_to_login()
        st.stop()

    try:
        response = requests.post(VALIDATE_API_URL, json={"api_key": api_key})
        if response.status_code == 200:
            user_data = response.json()
            required_fields = ["user_id", "name", "email", "role", "remaining_images"]
            if not all(field in user_data for field in required_fields):
                st.error("Invalid response from the server. Missing required fields.")
                st.stop()
            return user_data
        elif response.status_code == 401:
            hide_sidebar()
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
    st.experimental_set_query_params()
    hide_sidebar()
    redirect_to_login()

# Validate user session
user_data = validate_user()

# Initialize session state for tracking remaining usage for free users
if "remaining_images" not in st.session_state:
    if user_data["role"] == "free":
        st.session_state.remaining_images = int(user_data["remaining_images"])
    else:
        st.session_state.remaining_images = float('inf')  # Unlimited for Pro and Admin users

# Display user information and logout option
st.sidebar.markdown(f"**Logged in as:** {user_data['name']} ({user_data['email']})")
st.sidebar.write(f"**Role:** {user_data['role'].capitalize()}")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    handle_logout()

# Function to create grayscale background while keeping the subject colored
def create_grayscale_with_subject(original_image, subject_image):
    grayscale_background = ImageOps.grayscale(original_image).convert("RGBA")
    subject_alpha_mask = subject_image.getchannel("A")
    combined_image = Image.composite(subject_image, grayscale_background, subject_alpha_mask)
    return combined_image

# Function to process the uploaded image
def process_image(upload, text_sets):
    try:
        original_image = Image.open(upload).convert("RGBA")
        subject_image = remove(original_image)
        grayscale_with_subject = create_grayscale_with_subject(original_image, subject_image)

        text_layer = Image.new("RGBA", original_image.size, (255, 255, 255, 0))

        for text_set in text_sets:
            custom_text = text_set["text"]
            font_size = text_set["font_size"]
            font_color = text_set["font_color"]
            font_family = text_set["font_family"]
            font_stroke = text_set["font_stroke"]
            stroke_color = text_set["stroke_color"]
            text_opacity = text_set["text_opacity"]
            rotation = text_set["rotation"]
            x_position = text_set["x_position"]
            y_position = text_set["y_position"]
            text_transform = text_set["text_transform"]

            if text_transform == "uppercase":
                custom_text = custom_text.upper()
            elif text_transform == "lowercase":
                custom_text = custom_text.lower()
            elif text_transform == "capitalize":
                custom_text = custom_text.capitalize()

            font_path = os.path.join(FONTS_FOLDER, f"{font_family}.ttf")
            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception:
                st.warning(f"Could not load font: {font_family}. Using default font.")
                font = ImageFont.load_default()

            r, g, b = tuple(int(font_color[i:i+2], 16) for i in (1, 3, 5))
            font_color_with_opacity = (r, g, b, int(255 * text_opacity))

            sr, sg, sb = tuple(int(stroke_color[i:i+2], 16) for i in (1, 3, 5))
            stroke_color_with_opacity = (sr, sg, sb, int(255 * text_opacity))

            text_img = Image.new("RGBA", text_layer.size, (255, 255, 255, 0))
            text_draw = ImageDraw.Draw(text_img)

            text_x = (original_image.width / 2) + x_position
            text_y = (original_image.height / 2) + y_position

            text_draw.text(
                (text_x, text_y),
                custom_text,
                fill=font_color_with_opacity,
                font=font,
                anchor="mm",
                stroke_width=font_stroke,
                stroke_fill=stroke_color_with_opacity,
            )

            rotated_text_img = text_img.rotate(rotation, resample=Image.BICUBIC, center=(text_x, text_y))
            text_layer = Image.alpha_composite(text_layer, rotated_text_img)

        combined = Image.alpha_composite(original_image.convert("RGBA"), text_layer)
        combined = Image.alpha_composite(combined, subject_image.convert("RGBA"))

        st.write("## Final Image with Text 📝")
        st.image(combined, use_column_width=True)

        # Disable download buttons for free users who reached the limit
        download_disabled = user_data["role"] == "free" and st.session_state.remaining_images <= 0

        st.sidebar.download_button("Download Final Image", convert_image(combined), "final_image.png", "image/png", disabled=download_disabled)

        col1, col2 = st.columns(2)
        col1.write("### Grayscale Background Image 🌑")
        col1.image(grayscale_with_subject, use_column_width=True)
        col1.download_button("Download Grayscale Background", convert_image(grayscale_with_subject), "grayscale_with_subject.png", "image/png", disabled=download_disabled)

        col2.write("### Background Removed Image 👤")
        col2.image(subject_image, use_column_width=True)
        col2.download_button("Download Removed Background", convert_image(subject_image), "background_removed.png", "image/png", disabled=download_disabled)

        # Decrease remaining images count for free users
        if user_data["role"] == "free" and not download_disabled:
            st.session_state.remaining_images -= 1

    except Exception as e:
        st.error(f"An error occurred while processing the image: {str(e)}")

# File upload
my_upload = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

st.sidebar.write("### Manage Text Sets")
if "text_sets" not in st.session_state:
    st.session_state.text_sets = [
        {
            "text": "Your Custom Text",
            "font_size": 150,
            "font_color": "#FFFFFF",
            "font_family": "Arial Black",  # Default font set here
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
    if user_data["role"] == "free" and st.session_state.remaining_images <= 0:
        st.warning("You have reached your limit of 2 image edits as a free user. Please upgrade your account to add more text sets.")
    else:
        st.session_state.text_sets.append(
            {
                "text": "New Text",
                "font_size": 150,
                "font_color": "#FFFFFF",
                "font_family": "Arial Black",  # Default font set here
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
    if user_data["role"] == "free" and st.session_state.remaining_images <= 0:
        st.warning("You have reached your limit of 2 image edits as a free user. Please upgrade your account to remove text sets.")
    else:
        st.session_state.text_sets.pop(index)
        st.session_state.text_sets = st.session_state.text_sets

# Function to trigger re-rendering the image only on confirmation
def confirm_update(index):
    st.session_state[f"confirmed_{index}"] = True  # Mark the update as confirmed

# Button to add a new text set
st.sidebar.button("Add Text Set", on_click=add_text_set, disabled=user_data["role"] == "free" and st.session_state.remaining_images <= 0)

# Render each text set with collapsible editors
for i, text_set in enumerate(st.session_state.text_sets):
    with st.sidebar.expander(f"Text Set {i + 1}", expanded=True):
        if st.button(f"Remove Text Set {i + 1}", key=f"remove_text_set_{i}", disabled=user_data["role"] == "free" and st.session_state.remaining_images <= 0):
            remove_text_set(i)
            break

        disabled = user_data["role"] == "free" and st.session_state.remaining_images <= 0

        # Initialize confirmation state
        if f"confirmed_{i}" not in st.session_state:
            st.session_state[f"confirmed_{i}"] = True  # Initially confirmed

        # Text input
        new_text = st.text_input(f"Text {i + 1}", text_set["text"], key=f"text_{i}", disabled=disabled)
        if new_text != text_set["text"]:
            text_set["text"] = new_text
            st.session_state[f"confirmed_{i}"] = False
            if st.button("Confirm Update", key=f"confirm_text_{i}"):
                confirm_update(i)

        # Font family
        new_font_family = st.selectbox(
            f"Font Family {i + 1}",
            available_fonts,
            index=available_fonts.index(text_set["font_family"]) if text_set["font_family"] in available_fonts else 0,
            key=f"font_family_{i}",
            disabled=disabled
        )
        if new_font_family != text_set["font_family"]:
            text_set["font_family"] = new_font_family
            st.session_state[f"confirmed_{i}"] = False
            if st.button("Confirm Update", key=f"confirm_font_{i}"):
                confirm_update(i)

        # Font size
        new_font_size = st.slider(f"Font Size {i + 1}", 10, 1200, text_set["font_size"], key=f"font_size_{i}", disabled=disabled)
        if new_font_size != text_set["font_size"]:
            text_set["font_size"] = new_font_size
            st.session_state[f"confirmed_{i}"] = False
            if st.button("Confirm Update", key=f"confirm_font_size_{i}"):
                confirm_update(i)

        # Font color
        new_font_color = st.color_picker(f"Font Color {i + 1}", text_set["font_color"], key=f"font_color_{i}", disabled=disabled)
        if new_font_color != text_set["font_color"]:
            text_set["font_color"] = new_font_color
            st.session_state[f"confirmed_{i}"] = False
            if st.button("Confirm Update", key=f"confirm_color_{i}"):
                confirm_update(i)

        # Font stroke
        new_font_stroke = st.slider(f"Font Stroke {i + 1}", 0, 10, text_set["font_stroke"], key=f"font_stroke_{i}", disabled=disabled)
        if new_font_stroke != text_set["font_stroke"]:
            text_set["font_stroke"] = new_font_stroke
            st.session_state[f"confirmed_{i}"] = False
            if st.button("Confirm Update", key=f"confirm_stroke_{i}"):
                confirm_update(i)

        # Stroke color
        new_stroke_color = st.color_picker(f"Stroke Color {i + 1}", text_set["stroke_color"], key=f"stroke_color_{i}", disabled=disabled)
        if new_stroke_color != text_set["stroke_color"]:
            text_set["stroke_color"] = new_stroke_color
            st.session_state[f"confirmed_{i}"] = False
            if st.button("Confirm Update", key=f"confirm_stroke_color_{i}"):
                confirm_update(i)

        # Text opacity
        new_text_opacity = st.slider(
            f"Text Opacity {i + 1}", 0.1, 1.0, text_set["text_opacity"], step=0.1, key=f"text_opacity_{i}", disabled=disabled
        )
        if new_text_opacity != text_set["text_opacity"]:
            text_set["text_opacity"] = new_text_opacity
            st.session_state[f"confirmed_{i}"] = False
            if st.button("Confirm Update", key=f"confirm_opacity_{i}"):
                confirm_update(i)

        # Rotation
        new_rotation = st.slider(f"Rotate Text {i + 1}", 0, 360, text_set["rotation"], key=f"rotation_{i}", disabled=disabled)
        if new_rotation != text_set["rotation"]:
            text_set["rotation"] = new_rotation
            st.session_state[f"confirmed_{i}"] = False
            if st.button("Confirm Update", key=f"confirm_rotation_{i}"):
                confirm_update(i)

        # X position
        new_x_position = st.slider(f"X Position {i + 1}", -800, 800, text_set["x_position"], key=f"x_position_{i}", disabled=disabled)
        if new_x_position != text_set["x_position"]:
            text_set["x_position"] = new_x_position
            st.session_state[f"confirmed_{i}"] = False
            if st.button("Confirm Update", key=f"confirm_x_{i}"):
                confirm_update(i)

        # Y position
        new_y_position = st.slider(f"Y Position {i + 1}", -800, 800, text_set["y_position"], key=f"y_position_{i}", disabled=disabled)
        if new_y_position != text_set["y_position"]:
            text_set["y_position"] = new_y_position
            st.session_state[f"confirmed_{i}"] = False
            if st.button("Confirm Update", key=f"confirm_y_{i}"):
                confirm_update(i)

# Process the uploaded image only if all changes are confirmed
if my_upload is not None:
    if my_upload.size > MAX_FILE_SIZE:
        st.error("The uploaded file is too large. Please upload an image smaller than 7MB.")
    elif all(st.session_state.get(f"confirmed_{i}", True) for i in range(len(st.session_state.text_sets))):
        process_image(my_upload, st.session_state.text_sets)
    else:
        st.warning("Make changes and click 'Confirm Update' to apply your changes.")
else:
    st.write("Upload an image to begin editing!")
