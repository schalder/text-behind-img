import streamlit as st
import requests
from rembg import remove
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import os

# Backend URLs
CHECK_SESSION_URL = "https://app.ghlsaaskits.com/text-behind-img/check_session.php"
LOGIN_URL = "https://app.ghlsaaskits.com/text-behind-img/login.php"

# Set up Streamlit page
st.set_page_config(layout="wide", page_title="Image Subject and Text Editor")

# Logging for Debugging
def log_message(message):
    st.write(f"**Debug:** {message}")

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


# Function to validate session using the token from the URL
def validate_session(token):
    try:
        log_message(f"Validating token: {token}")
        response = requests.get(CHECK_SESSION_URL, params={"token": token})
        log_message(f"Response from backend: {response.status_code}, {response.text}")
        if response.status_code == 200:
            user_data = response.json()
            if "error" not in user_data:
                return user_data
        return None
    except Exception as e:
        st.error(f"Error validating session: {e}")
        return None


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
        st.sidebar.download_button("Download Final Image", convert_image(combined), "final_image.png", "image/png")

        col1, col2 = st.columns(2)
        col1.write("### Grayscale Background Image 🌑")
        col1.image(grayscale_with_subject, use_column_width=True)
        col1.download_button("Download Grayscale Background", convert_image(grayscale_with_subject), "grayscale_with_subject.png", "image/png")

        col2.write("### Background Removed Image 👤")
        col2.image(subject_image, use_column_width=True)
        col2.download_button("Download Removed Background", convert_image(subject_image), "background_removed.png", "image/png")

    except Exception as e:
        st.error(f"An error occurred while processing the image: {e}")


# Get token from the URL
query_params = st.experimental_get_query_params()
token = query_params.get("token", [None])[0]

if not token:
    # If no token, redirect to login page
    st.error("You are not logged in. Redirecting to login...")
    st.stop()

# Validate session with the backend
user_data = validate_session(token)
if not user_data:
    st.error("Session expired or invalid. Please log in again.")
    st.stop()

# Display user information and logout option
st.sidebar.markdown(f"**Logged in as:** {user_data['name']} ({user_data['email']})")
if st.sidebar.button("Logout"):
    st.experimental_set_query_params()  # Clear parameters
    st.success("Logged out successfully! Redirecting...")
    st.stop()

# Main app functionality
st.title("Text Behind Image Editor")
st.write(f"Welcome, **{user_data['name']}**!")

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
        text_set["text_opacity"] = st.slider(
            f"Text Opacity {i + 1}", 0.1, 1.0, text_set["text_opacity"], step=0.1, key=f"text_opacity_{i}"
        )
        text_set["rotation"] = st.slider(f"Rotate Text {i + 1}", 0, 360, text_set["rotation"], key=f"rotation_{i}")
        text_set["x_position"] = st.slider(f"X Position {i + 1}", -400, 400, text_set["x_position"], key=f"x_position_{i}")
        text_set["y_position"] = st.slider(f"Y Position {i + 1}", -400, 400, text_set["y_position"], key=f"y_position_{i}")

if my_upload:
    if my_upload.size > MAX_FILE_SIZE:
        st.error("The uploaded file is too large. Please upload an image smaller than 5MB.")
    else:
        process_image(my_upload, st.session_state.text_sets)
else:
    st.write("Upload an image to begin editing!")
