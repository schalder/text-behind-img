import streamlit as st
import requests
from rembg import remove
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import os

# Backend URLs
VALIDATE_API_URL = "https://app.ghlsaaskits.com/text-behind-img/validate_api_key.php"
UPDATE_DOWNLOAD_URL = "https://app.ghlsaaskits.com/text-behind-img/update_download_count.php"
LOGIN_URL = "https://app.ghlsaaskits.com/text-behind-img/login.php"
UPGRADE_URL = "https://ghlsaaskits.com/upgrade-tbi"

# Set up Streamlit page
st.set_page_config(layout="wide", page_title="Image Subject and Text Editor")

MAX_FILE_SIZE = 7 * 1024 * 1024  # 7MB max file size

# Ensure the fonts folder exists
FONTS_FOLDER = "fonts"
if not os.path.exists(FONTS_FOLDER):
    os.makedirs(FONTS_FOLDER)

# Load available fonts
available_fonts = [f.replace(".ttf", "") for f in os.listdir(FONTS_FOLDER) if f.endswith(".ttf")]

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
            required_fields = ["user_id", "name", "email", "role", "remaining_images", "download_count"]
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

# Function to update the download count in the database
def update_download_count(api_key):
    try:
        response = requests.post(UPDATE_DOWNLOAD_URL, json={"api_key": api_key})
        if response.status_code == 200:
            return response.json().get("success", False)
        else:
            st.error(f"Failed to update download count: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error updating download count: {e}")
        return False

# Function to handle download button click
def handle_download(img, file_name, format="PNG"):
    api_key = st.experimental_get_query_params().get("api_key", [None])[0]

    if user_data["role"] == "free" and user_data["download_count"] >= 2:
        st.error("You have reached your free download limit. Please upgrade your account.")
        st.markdown(f"""
            <a href="{UPGRADE_URL}" style="text-decoration: none;">
               <button style="
                   padding: 10px 20px; 
                   background-color: #007bff; 
                   color: white; 
                   border: none; 
                   border-radius: 5px; 
                   font-size: 16px; 
                   cursor: pointer;">
                   Upgrade Account
               </button>
            </a>
        """, unsafe_allow_html=True)
    else:
        success = update_download_count(api_key)
        if success:
            user_data["download_count"] += 1  # Update local session
            st.sidebar.download_button(
                label="Download Final Image",
                data=convert_image(img, format),
                file_name=file_name,
                mime=f"image/{format.lower()}",
            )
        else:
            st.error("Failed to update download count. Please try again.")

# Function to process the uploaded image
def process_image(upload, text_sets):
    try:
        original_image = Image.open(upload).convert("RGBA")
        subject_image = remove(original_image)
        grayscale_with_subject = ImageOps.grayscale(original_image).convert("RGBA")
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
        handle_download(combined, "final_image.png")
    except Exception as e:
        st.error(f"An error occurred while processing the image: {str(e)}")

# File upload
my_upload = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

if my_upload is not None:
    process_image(my_upload, st.session_state.text_sets)
else:
    st.write("Upload an image to begin editing!")
