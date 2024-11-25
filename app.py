import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import requests

# Set up Streamlit page
st.set_page_config(layout="wide", page_title="Image Subject and Text Editor")

# Sidebar upload/download instructions
st.sidebar.write("## Upload and download :gear:")

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB max file size

@st.cache_data
def load_font(font_path, font_size):
    return ImageFont.truetype(font_path, font_size)

def optimize_image(image, max_size=(1024, 1024)):
    image.thumbnail(max_size, Image.ANTIALIAS)
    return image

def remove_background(image):
    endpoint = "http://localhost:5000"  # Rembg server URL
    with BytesIO() as img_byte_arr:
        image.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)
        response = requests.post(endpoint, files={"image": img_byte_arr})
        return Image.open(BytesIO(response.content))

# Function to process the uploaded image
def process_image(upload, custom_text, font_size, font_color, font_family, font_weight, text_opacity, rotation, x_position, y_position):
    # Load the uploaded image
    image = Image.open(upload).convert("RGBA")
    image = optimize_image(image)

    # Split subject and background using rembg server
    subject_image = remove_background(image)
    background_image = image

    # Display the original image and processed layers
    col1.write("Original Image :camera:")
    col1.image(image, use_column_width=True)

    col2.write("Subject (Foreground) :bust_in_silhouette:")
    col2.image(subject_image, use_column_width=True)

    col3.write("Background Layer :art:")
    col3.image(background_image, use_column_width=True)

    # Add custom text between subject and background
    text_layer = Image.new("RGBA", background_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_layer)

    # Load font
    font_path = os.path.join("fonts", f"{font_family}.ttf")
    font = load_font(font_path, font_size)

    # Adjust font color with opacity
    r, g, b = tuple(int(font_color[i:i+2], 16) for i in (1, 3, 5))  # Convert #RRGGBB to RGB
    font_color_with_opacity = (r, g, b, int(255 * text_opacity))

    # Create a separate image for the text and rotate it around its center
    text_img = Image.new("RGBA", text_layer.size, (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_img)

    # Calculate text position
    text_x = (background_image.width / 2) + x_position
    text_y = (background_image.height / 2) + y_position

    # Add text to the new layer
    text_draw.text((text_x, text_y), custom_text, fill=font_color_with_opacity, font=font, anchor="mm")
    rotated_text_img = text_img.rotate(rotation, resample=Image.BICUBIC, center=(text_x, text_y))

    # Merge the layers: Background + Text + Subject
    combined = Image.alpha_composite(background_image.convert("RGBA"), rotated_text_img)
    combined = Image.alpha_composite(combined, subject_image.convert("RGBA"))

    # Display the final result
    st.write("Final Image with Text :pencil:")
    st.image(combined, use_column_width=True)

    # Add download button for the final image
    st.sidebar.download_button(
        "Download Final Image",
        convert_image(combined),
        "final_image.png",
        "image/png",
    )


# Layout: Three columns for display
col1, col2, col3 = st.columns(3)

# File upload in the sidebar
my_upload = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

# Sidebar customization options
st.sidebar.write("### Customize Your Text")
custom_text = st.sidebar.text_input("Enter your text", "Your Custom Text")
font_family = st.sidebar.selectbox(
    "Font Family",
    [f.replace(".ttf", "") for f in os.listdir("fonts") if f.endswith(".ttf")],
)
font_size = st.sidebar.slider("Font Size", 10, 200, 50)
font_color = st.sidebar.color_picker("Font Color", "#FFFFFF")
text_opacity = st.sidebar.slider("Text Opacity", 0.1, 1.0, 1.0, step=0.1)
rotation = st.sidebar.slider("Rotate Text", 0, 360, 0)
x_position = st.sidebar.slider("X Position", -400, 400, 0)
y_position = st.sidebar.slider("Y Position", -400, 400, 0)

# Process the uploaded image
if my_upload is not None:
    if my_upload.size > MAX_FILE_SIZE:
        st.error("The uploaded file is too large. Please upload an image smaller than 5MB.")
    else:
        process_image(
            upload=my_upload,
            custom_text=custom_text,
            font_size=font_size,
            font_color=font_color,
            font_family=font_family,
            font_weight=400,  # Placeholder for font weight
            text_opacity=text_opacity,
            rotation=rotation,
            x_position=x_position,
            y_position=y_position,
        )
else:
    st.write("Upload an image to begin editing!")
