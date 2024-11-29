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
        st.error("API key missing. Please log in.")
        st.stop()

    try:
        response = requests.post(VALIDATE_API_URL, json={"api_key": api_key})
        if response.status_code == 200:
            user_data = response.json()
            required_fields = ["user_id", "name", "email", "role", "remaining_images"]
            if not all(field in user_data for field in required_fields):
                st.error("Invalid server response.")
                st.stop()
            return user_data
        elif response.status_code == 401:
            st.error("Invalid or expired API key.")
            st.stop()
        else:
            st.error(f"Unexpected error: {response.text}.")
            st.stop()
    except Exception as e:
        st.error(f"Error validating session: {e}.")
        st.stop()

user_data = validate_user()

# Initialize text_sets (confirmed state) and temp_text_sets (temporary changes)
if "text_sets" not in st.session_state:
    st.session_state.text_sets = [
        {
            "text": "Your Custom Text",
            "font_size": 150,
            "font_color": "#FFFFFF",
            "font_family": "Arial Black",
            "font_stroke": 2,
            "stroke_color": "#000000",
            "text_opacity": 1.0,
            "rotation": 0,
            "x_position": 0,
            "y_position": 0,
            "text_transform": "none",
        }
    ]

if "temp_text_sets" not in st.session_state:
    st.session_state.temp_text_sets = st.session_state.text_sets.copy()

# Function to create grayscale background while keeping the subject colored
def create_grayscale_with_subject(original_image, subject_image):
    grayscale_background = ImageOps.grayscale(original_image).convert("RGBA")
    subject_alpha_mask = subject_image.getchannel("A")
    combined_image = Image.composite(subject_image, grayscale_background, subject_alpha_mask)
    return combined_image

# Function to process the uploaded image using the confirmed text_sets
def process_image(upload):
    try:
        original_image = Image.open(upload).convert("RGBA")
        subject_image = remove(original_image)
        grayscale_with_subject = create_grayscale_with_subject(original_image, subject_image)

        text_layer = Image.new("RGBA", original_image.size, (255, 255, 255, 0))
        for text_set in st.session_state.text_sets:
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

        st.write("## Text Behind Image 📝")
        st.image(combined, use_column_width=True)
    except Exception as e:
        st.error(f"An error occurred while processing the image: {str(e)}")

# File upload
my_upload = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

# Sidebar for managing text sets
st.sidebar.write("### Manage Text Sets")
for i, text_set in enumerate(st.session_state.temp_text_sets):
    with st.sidebar.expander(f"Text Set {i + 1}", expanded=True):
        text_set["text"] = st.text_input(f"Text {i + 1}", text_set["text"], key=f"text_{i}")
        text_set["font_family"] = st.selectbox(f"Font Family {i + 1}", available_fonts, key=f"font_family_{i}")
        text_set["font_size"] = st.slider(f"Font Size {i + 1}", 10, 1200, text_set["font_size"], key=f"font_size_{i}")
        text_set["font_color"] = st.color_picker(f"Font Color {i + 1}", text_set["font_color"], key=f"font_color_{i}")
        text_set["font_stroke"] = st.slider(f"Font Stroke {i + 1}", 0, 10, text_set["font_stroke"], key=f"font_stroke_{i}")
        text_set["stroke_color"] = st.color_picker(f"Stroke Color {i + 1}", text_set["stroke_color"], key=f"stroke_color_{i}")
        text_set["text_opacity"] = st.slider(f"Text Opacity {i + 1}", 0.1, 1.0, text_set["text_opacity"], key=f"text_opacity_{i}")
        text_set["rotation"] = st.slider(f"Rotation {i + 1}", 0, 360, text_set["rotation"], key=f"rotation_{i}")
        text_set["x_position"] = st.slider(f"X Position {i + 1}", -800, 800, text_set["x_position"], key=f"x_position_{i}")
        text_set["y_position"] = st.slider(f"Y Position {i + 1}", -800, 800, text_set["y_position"], key=f"y_position_{i}")

# Confirm and Cancel buttons
if st.sidebar.button("Confirm Changes"):
    st.session_state.text_sets = st.session_state.temp_text_sets.copy()
    st.success("Changes confirmed!")

if st.sidebar.button("Cancel Changes"):
    st.session_state.temp_text_sets = st.session_state.text_sets.copy()
    st.info("Changes reverted to the previous state.")

# Render the processed image only if a file is uploaded
if my_upload is not None:
    process_image(my_upload)
else:
    st.write("Upload an image to begin editing!")
