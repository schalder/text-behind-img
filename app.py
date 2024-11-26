import streamlit as st
from rembg import remove
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from io import BytesIO
import os

# Set up Streamlit page
st.set_page_config(layout="wide", page_title="Image Subject and Text Editor")

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


# Function to create grayscale background while keeping the subject colored
def create_grayscale_with_subject(original_image, subject_image):
    # Convert the original image to grayscale
    grayscale_background = ImageOps.grayscale(original_image).convert("RGBA")

    # Extract the alpha channel from the subject
    subject_alpha_mask = subject_image.getchannel("A")

    # Composite the subject onto the grayscale background
    combined_image = Image.composite(subject_image, grayscale_background, subject_alpha_mask)
    return combined_image


# Function to process the uploaded image
def process_image(upload, text_sets):
    try:
        # Load the uploaded image
        original_image = Image.open(upload).convert("RGBA")

        # Split subject and background using rembg
        subject_image = remove(original_image)

        # Create grayscale background with colored subject
        grayscale_with_subject = create_grayscale_with_subject(original_image, subject_image)

        # Add custom text between subject and background
        text_layer = Image.new("RGBA", original_image.size, (255, 255, 255, 0))

        for text_set in text_sets:
            # Extract customization options for the text set
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
            shadow_enabled = text_set["shadow_enabled"]
            shadow_color = text_set["shadow_color"]
            shadow_x_offset = text_set["shadow_x_offset"]
            shadow_y_offset = text_set["shadow_y_offset"]
            shadow_blur = text_set["shadow_blur"]

            # Transform text
            if text_transform == "uppercase":
                custom_text = custom_text.upper()
            elif text_transform == "lowercase":
                custom_text = custom_text.lower()
            elif text_transform == "capitalize":
                custom_text = custom_text.capitalize()

            # Set font using uploaded fonts in the `fonts` folder
            font_path = os.path.join(FONTS_FOLDER, f"{font_family}.ttf")
            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception:
                st.warning(f"Could not load font: {font_family}. Using default font.")
                font = ImageFont.load_default()

            # Adjust font color with opacity
            r, g, b = tuple(int(font_color[i:i+2], 16) for i in (1, 3, 5))  # Convert #RRGGBB to RGB
            font_color_with_opacity = (r, g, b, int(255 * text_opacity))

            # Adjust stroke color
            sr, sg, sb = tuple(int(stroke_color[i:i+2], 16) for i in (1, 3, 5))  # Convert #RRGGBB to RGB
            stroke_color_with_opacity = (sr, sg, sb, int(255 * text_opacity))

            # Create a separate image for the text and apply effects
            text_img = Image.new("RGBA", text_layer.size, (255, 255, 255, 0))
            text_draw = ImageDraw.Draw(text_img)

            # Calculate text position
            text_x = (original_image.width / 2) + x_position
            text_y = (original_image.height / 2) + y_position

            # Apply shadow if enabled
            if shadow_enabled:
                shadow_layer = Image.new("RGBA", text_img.size, (255, 255, 255, 0))
                shadow_draw = ImageDraw.Draw(shadow_layer)
                shadow_draw.text(
                    (text_x + shadow_x_offset, text_y + shadow_y_offset),
                    custom_text,
                    fill=shadow_color,
                    font=font,
                    anchor="mm",
                )
                # Apply blur to the shadow
                shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
                text_img = Image.alpha_composite(shadow_layer, text_img)

            # Add text with stroke
            text_draw.text(
                (text_x, text_y),
                custom_text,
                fill=font_color_with_opacity,
                font=font,
                anchor="mm",
                stroke_width=font_stroke,
                stroke_fill=stroke_color_with_opacity,
            )

            # Rotate text and merge layers
            rotated_text_img = text_img.rotate(rotation, resample=Image.BICUBIC, center=(text_x, text_y))
            text_layer = Image.alpha_composite(text_layer, rotated_text_img)

        # Merge the layers: Background + Text + Subject
        combined = Image.alpha_composite(original_image.convert("RGBA"), text_layer)
        combined = Image.alpha_composite(combined, subject_image.convert("RGBA"))

        # Display the final result
        st.write("## Final Image with Text 📝")
        st.image(combined, use_column_width=True)

        # Add download button for the final image
        st.sidebar.download_button(
            "Download Final Image",
            convert_image(combined),
            "final_image.png",
            "image/png",
        )

        # Two-column layout for Grayscale + Subject Image
        col1, col2 = st.columns(2)

        # Grayscale Background + Colored Subject
        col1.write("### Grayscale Background Image 🌑")
        col1.image(grayscale_with_subject, use_column_width=True)
        col1.download_button(
            "Download Grayscale Background",
            convert_image(grayscale_with_subject),
            "grayscale_with_subject.png",
            "image/png",
        )

        # Background Removed Image
        col2.write("### Background Removed Image 👤")
        col2.image(subject_image, use_column_width=True)
        col2.download_button(
            "Download Removed Background",
            convert_image(subject_image),
            "background_removed.png",
            "image/png",
        )

    except Exception as e:
        st.error(f"An error occurred while processing the image: {str(e)}")


# File upload in the sidebar
my_upload = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

# Manage multiple text sets
st.sidebar.write("### Manage Text Sets")

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
            "shadow_enabled": False,
            "shadow_color": "#000000",
            "shadow_x_offset": 5,
            "shadow_y_offset": 5,
            "shadow_blur": 5,
        }
    ]

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
            "shadow_enabled": False,
            "shadow_color": "#000000",
            "shadow_x_offset": 5,
            "shadow_y_offset": 5,
            "shadow_blur": 5,
        }
    )

# Function to handle removing a text set
def remove_text_set(index):
    st.session_state.text_sets.pop(index)

# Button to add a new text set
st.sidebar.button("Add Text Set", on_click=add_text_set)

# Render each text set with collapsible editors
for i, text_set in enumerate(st.session_state.text_sets):
    with st.sidebar.expander(f"Text Set {i + 1}", expanded=True):
        if st.button(f"Remove Text Set {i + 1}", key=f"remove_text_set_{i}"):
            remove_text_set(i)
            break

        text_set["text"] = st.text_input(f"Text {i + 1}", text_set["text"], key=f"text_{i}")
        text_set["font_family"] = st.selectbox(
            f"Font Family {i + 1}",
            [f.replace(".ttf", "") for f in os.listdir(FONTS_FOLDER) if f.endswith(".ttf")],
            index=0,
            key=f"font_family_{i}",
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
        text_set["text_transform"] = st.selectbox(
            f"Text Transform {i + 1}", ["none", "uppercase", "lowercase", "capitalize"], key=f"text_transform_{i}"
        )
        text_set["shadow_enabled"] = st.checkbox(f"Enable Shadow {i + 1}", text_set["shadow_enabled"], key=f"shadow_enabled_{i}")
        if text_set["shadow_enabled"]:
            text_set["shadow_color"] = st.color_picker(f"Shadow Color {i + 1}", text_set["shadow_color"], key=f"shadow_color_{i}")
            text_set["shadow_x_offset"] = st.slider(
                f"Shadow X Offset {i + 1}", -50, 50, text_set["shadow_x_offset"], key=f"shadow_x_offset_{i}"
            )
            text_set["shadow_y_offset"] = st.slider(
                f"Shadow Y Offset {i + 1}", -50, 50, text_set["shadow_y_offset"], key=f"shadow_y_offset_{i}"
            )
            text_set["shadow_blur"] = st.slider(f"Shadow Blur {i + 1}", 0, 20, text_set["shadow_blur"], key=f"shadow_blur_{i}")

# Process the uploaded image
if my_upload is not None:
    if my_upload.size > MAX_FILE_SIZE:
        st.error("The uploaded file is too large. Please upload an image smaller than 5MB.")
    else:
        process_image(my_upload, st.session_state.text_sets)
else:
    st.write("Upload an image to begin editing!")
