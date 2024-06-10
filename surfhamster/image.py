import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


def create_grid_image(image_width, image_height, color_circle, color_number, n, file_name):
    # We need a simple grid: numbers from 1 to 99 in points on an intersection of NxN grid.
    # The font size may be 1/5 of the size of the height of the cell.
    # Therefore, we need the size of the image and colors, and the file_name. 

    cell_width = image_width // n
    cell_height = image_height // n
    font_size = max(cell_height // 5, 20)
    circle_radius = font_size * 7 // 10

    # Create a blank image with transparent background
    img = Image.new('RGBA', (image_width, image_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Load a font
    font = ImageFont.truetype("font/arialbd.ttf", font_size)

    # Set the number of cells in each dimension
    num_cells_x = n - 1 
    num_cells_y = n - 1

    # Draw the numbers in the center of each cell
    for i in range(num_cells_x):
        for j in range(num_cells_y):
            number = i * num_cells_y + j + 1
            text = str(number)
            x = (i + 1) * cell_width
            y = (j + 1) * cell_height
            draw.ellipse([x - circle_radius, y - circle_radius, 
                          x + circle_radius, y + circle_radius], 
                          fill=color_circle)
            offset_x = font_size / 4 if number < 10 else font_size / 2
            draw.text((x - offset_x, y - font_size / 2), text, font=font, fill=color_number)

    # Save the image
    img.save(file_name)


def superimpose_images(image1_path, image2_path, opacity):
    # Open the images
    image1 = Image.open(image1_path)
    image2 = Image.open(image2_path)

    # Ensure both images have the same size
    if image1.size != image2.size:
        raise ValueError("Images must have the same dimensions.")

    # Convert the images to RGBA mode if they are not already
    image1 = image1.convert("RGBA")
    image2 = image2.convert("RGBA")

    # Create a new image with the same size as the input images
    merged_image = Image.new("RGBA", image1.size)

    # Convert image1 to grayscale
    image1 = image1.convert("L")

    # Paste image1 onto the merged image
    merged_image.paste(image1, (0, 0))

    # Create a new image for image2 with adjusted opacity
    image2_with_opacity = Image.blend(Image.new("RGBA", image2.size, (0, 0, 0, 0)), image2, opacity)

    # Paste image2 with opacity onto the merged image
    merged_image = Image.alpha_composite(merged_image, image2_with_opacity)

    return merged_image


def image_to_b64(img: Image.Image, image_format="PNG") -> str:
    """Converts a PIL Image to a base64-encoded string with MIME type included.

    Args:
        img (Image.Image): The PIL Image object to convert.
        image_format (str): The format to use when saving the image (e.g., 'PNG', 'JPEG').

    Returns:
        str: A base64-encoded string of the image with MIME type.
    """
    buffer = BytesIO()
    img.save(buffer, format=image_format)
    image_data = buffer.getvalue()
    buffer.close()

    mime_type = f"image/{image_format.lower()}"
    base64_encoded_data = base64.b64encode(image_data).decode("utf-8")
    return f"data:{mime_type};base64,{base64_encoded_data}"


def b64_to_image(base64_str: str) -> Image.Image:
    """Converts a base64 string to a PIL Image object.

    Args:
        base64_str (str): The base64 string, potentially with MIME type as part of a data URI.

    Returns:
        Image.Image: The converted PIL Image object.
    """
    # Strip the MIME type prefix if present
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]

    image_data = base64.b64decode(base64_str)
    image = Image.open(BytesIO(image_data))
    return image


def load_image_base64(filepath: str) -> str:
    # Load the image from the file path
    image = Image.open(filepath)
    buffered = BytesIO()

    # Save image to the buffer
    image_format = image.format if image.format else "PNG"
    image.save(buffered, format=image_format)

    # Encode the image to base64
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # Prepare the mime type
    mime_type = f"image/{image_format.lower()}"

    # Return base64 string with mime type
    return f"data:{mime_type};base64,{img_str}"
