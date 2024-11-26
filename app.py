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

# Ensure the fonts folder exists
FONTS_FOLDER = "fonts"
if not os.path.exists(FONTS_FOLDER):
    os.makedirs(FONTS_FOLDER)

# Function to validate session
def validate_session():
    try:
        # Send the stored cookies to validate the session
        response = requests.get(CHECK_SESSION_URL, cookies=st.session_state.cookies)
        if response.status_code == 200:
            user_data = response.json()
            st.session_state.user_data = user_data
            return True
        else:
            return False
    except Exception as e:
        st.error("Unable to validate session. Please check your backend configuration.")
        return False

# Function to logout
def logout():
    try:
        requests.get(LOGOUT_URL, cookies=st.session_state.cookies)
        st.session_state.clear()
        st.experimental_rerun()
    except Exception as e:
        st.error("An error occurred during logout.")

# Initialize session state for cookies and user data
if "cookies" not in st.session_state:
    st.session_state.cookies = None
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# Redirect to login page if not logged in
if not st.session_state.cookies or not validate_session():
    st.warning("Redirecting to login page...")
    st.experimental_redirect(LOGIN_URL)
    st.stop()

# User data
user_data = st.session_state.user_data
role = user_data.get("role", "free")
remaining_images = user_data.get("remaining_images", "unlimited")

# Sidebar for user information and logout
st.sidebar.markdown(f"**Logged in as:** {user_data['name']} ({user_data['email']})")
if st.sidebar.button("Logout"):
    logout()

# Sidebar upload/download instructions
st.sidebar.write("## Upload and download :gear:")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB max file size

# Function to process image
def process_image(upload, text_sets):
    try:
        original_image = Image.open(upload).convert("RGBA")
        subject_image = remove(original_image)

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

            # Transform text
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

        st.sidebar.download_button(
            "Download Final Image",
            convert_image(combined),
            "final_image.png",
            "image/png",
        )

    except Exception as e:
        st.error(f"An error occurred while processing the image: {str(e)}")

# File upload
my_upload = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

if my_upload is not None:
    if role == "free" and remaining_images == 0:
        st.warning("Upgrade to Pro to use this feature.")
    else:
        process_image(my_upload, st.session_state.text_sets)
else:
    st.write("Upload an image to begin editing!")
