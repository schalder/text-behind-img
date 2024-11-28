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

# Process the image and return updated preview
def process_image(upload, text_sets):
    try:
        original_image = Image.open(upload).convert("RGBA")
        subject_image = remove(original_image)

        text_layer = Image.new("RGBA", original_image.size, (255, 255, 255, 0))
        for text_set in text_sets:
            font_path = os.path.join(FONTS_FOLDER, f"{text_set['font_family']}.ttf")
            try:
                font = ImageFont.truetype(font_path, text_set['font_size'])
            except Exception:
                font = ImageFont.load_default()

            draw = ImageDraw.Draw(text_layer)
            r, g, b = tuple(int(text_set['font_color'][i:i+2], 16) for i in (1, 3, 5))
            color = (r, g, b, int(255 * text_set['text_opacity']))

            sr, sg, sb = tuple(int(text_set['stroke_color'][i:i+2], 16) for i in (1, 3, 5))
            stroke_color = (sr, sg, sb, int(255 * text_set['text_opacity']))

            draw.text(
                (original_image.width / 2 + text_set['x_position'], original_image.height / 2 + text_set['y_position']),
                text_set['text'],
                fill=color,
                font=font,
                stroke_width=text_set['font_stroke'],
                stroke_fill=stroke_color,
                anchor="mm",
            )

        combined_image = Image.alpha_composite(original_image.convert("RGBA"), text_layer)

        return combined_image

    except Exception as e:
        st.error(f"An error occurred while processing the image: {str(e)}")
        return None


# File upload
my_upload = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

# Session state initialization
if "original_text_sets" not in st.session_state:
    st.session_state.original_text_sets = []

if "working_text_sets" not in st.session_state:
    st.session_state.working_text_sets = []

if "preview_image" not in st.session_state:
    st.session_state.preview_image = None

# Reset to original text sets on cancel
def cancel_changes():
    st.session_state.working_text_sets = st.session_state.original_text_sets.copy()

# Apply changes and update preview
def confirm_changes():
    st.session_state.original_text_sets = st.session_state.working_text_sets.copy()
    st.session_state.preview_image = process_image(my_upload, st.session_state.original_text_sets)

# Initial setup
if my_upload:
    if not st.session_state.original_text_sets:
        st.session_state.original_text_sets = [
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
            }
        ]
        st.session_state.working_text_sets = st.session_state.original_text_sets.copy()
        st.session_state.preview_image = process_image(my_upload, st.session_state.original_text_sets)

# Sidebar customization controls
if my_upload:
    for idx, text_set in enumerate(st.session_state.working_text_sets):
        with st.sidebar.expander(f"Text Set {idx + 1}", expanded=True):
            text_set["text"] = st.text_input(f"Text {idx + 1}", text_set["text"], key=f"text_{idx}")
            text_set["font_family"] = st.selectbox(
                f"Font Family {idx + 1}", available_fonts, key=f"font_family_{idx}"
            )
            text_set["font_size"] = st.slider(f"Font Size {idx + 1}", 10, 300, text_set["font_size"], key=f"font_size_{idx}")
            text_set["font_color"] = st.color_picker(f"Font Color {idx + 1}", text_set["font_color"], key=f"font_color_{idx}")
            text_set["font_stroke"] = st.slider(f"Font Stroke {idx + 1}", 0, 10, text_set["font_stroke"], key=f"font_stroke_{idx}")
            text_set["stroke_color"] = st.color_picker(f"Stroke Color {idx + 1}", text_set["stroke_color"], key=f"stroke_color_{idx}")
            text_set["text_opacity"] = st.slider(f"Text Opacity {idx + 1}", 0.1, 1.0, text_set["text_opacity"], key=f"text_opacity_{idx}")
            text_set["x_position"] = st.slider(f"X Position {idx + 1}", -500, 500, text_set["x_position"], key=f"x_position_{idx}")
            text_set["y_position"] = st.slider(f"Y Position {idx + 1}", -500, 500, text_set["y_position"], key=f"y_position_{idx}")

    # Confirm and Cancel buttons
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.button("Confirm Updates", on_click=confirm_changes)
    with col2:
        st.button("Cancel", on_click=cancel_changes)

# Preview area
if st.session_state.preview_image:
    st.write("## Preview")
    st.image(st.session_state.preview_image, use_column_width=True)
else:
    st.write("Upload an image to start customizing!")
