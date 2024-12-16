import streamlit as st
import requests
from rembg import remove
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import os

# Backend URLs
VALIDATE_API_URL = "https://app.ghlsaaskits.com/text-behind-img/validate_api_key.php"
UPDATE_DOWNLOAD_COUNT_URL = "https://app.ghlsaaskits.com/text-behind-img/update_download_count.php"
LOGIN_URL = "https://app.ghlsaaskits.com/text-behind-img/login.php"
UPGRADE_URL = "https://ghlsaaskits.com/upgrade-tbi"
ADMIN_DASHBOARD_URL = "https://app.ghlsaaskits.com/admin.php"

# Set up Streamlit page
st.set_page_config(layout="wide", page_title="Image Subject and Text Editor")

# Sidebar upload/download instructions
st.sidebar.write("## GHL SaasKits :gear:")

MAX_FILE_SIZE = 7 * 1024 * 1024  # 7MB max file size

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
    """Redirect the user to the login page by displaying a link."""
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
    query_params = st.query_params  # Use the modern query_params API
    api_key = query_params.get("api_key", [None])[0]
    if not api_key:
        hide_sidebar()
        st.warning("Click the button below to login")
        redirect_to_login()

    try:
        response = requests.post(VALIDATE_API_URL, json={"api_key": api_key})
        if response.status_code == 200:
            user_data = response.json()
            required_fields = ["user_id", "name", "email", "role", "remaining_images", "download_count"]
            if not all(field in user_data for field in required_fields):
                st.error("Invalid response from the server. Missing required fields.")
                st.stop()
            
            # Convert "unlimited" to float('inf') for Pro/Admin users
            if user_data["remaining_images"] == "unlimited":
                user_data["remaining_images"] = float('inf')
            else:
                user_data["remaining_images"] = int(user_data["remaining_images"])
            return user_data
        elif response.status_code == 401:
            hide_sidebar()
            st.warning("Invalid or expired API key. Redirecting to login...")
            redirect_to_login()
        else:
            st.error(f"Unexpected error: {response.text}. Please contact support.")
            st.stop()
    except Exception as e:
        st.error(f"Unable to validate session: {e}. Please try again.")
        st.stop()

# Logout functionality
def handle_logout():
    """Handle user logout."""
    st.session_state.clear()  # Clear session state to reset the user state
    redirect_to_login()

# Validate user session
user_data = validate_user()

# Initialize session state for tracking remaining usage for free users
if "remaining_images" not in st.session_state:
    st.session_state.remaining_images = user_data["remaining_images"]

# Logout button in the sidebar
st.sidebar.markdown(f"**Logged in as:** {user_data['name']}")
st.sidebar.write(f"**Plan:** {user_data['role'].capitalize()} **Unlimited**")

if st.sidebar.button("Logout"):
    handle_logout()

# Function to update download count in the backend
def update_download_count():
    try:
        response = requests.post(UPDATE_DOWNLOAD_COUNT_URL, json={"user_id": user_data["user_id"]})
        if response.status_code == 200:
            updated_data = response.json()
            if user_data["role"] == "free":
                st.session_state.remaining_images = int(updated_data.get("remaining_images", st.session_state.remaining_images))
        else:
            st.error("Error updating download count. Please contact support.")
    except Exception as e:
        st.error(f"Error updating download count: {e}")

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
 
        st.write("## Text Behind Image 📝")
        st.image(combined, use_column_width=True)

        # Disable download buttons for free users who reached the limit
        download_disabled = user_data["role"] == "free" and st.session_state.remaining_images <= 0

        if st.sidebar.download_button("Download Final Image", convert_image(combined), "final_image.png", "image/png", disabled=download_disabled):
            update_download_count()

    except Exception as e:
        st.error(f"An error occurred while processing the image: {str(e)}")

# File upload
my_upload = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

st.sidebar.write("### Manage Text Sets")
if "text_sets" not in st.session_state:
    st.session_state.text_sets = []

if my_upload:
    if my_upload.size > MAX_FILE_SIZE:
        st.error("The uploaded file is too large. Please upload an image smaller than 7MB.")
    elif st.session_state.remaining_images > 0 or user_data["role"] != "free":
        process_image(my_upload, st.session_state.text_sets)
    else:
        st.error("You have reached your limit.")
