import os
import time
import requests
import hashlib
from pydantic import BaseModel, Field
from random import randint
from PIL import Image

from agentdesk.device import Desktop
from taskara import Task
from toolfuse import Tool, action
from mllm import RoleMessage, RoleThread, Router
from rich.console import Console
from rich.json import JSON

from .ocr import find_boxes_with_text, draw_bbs
from .image import b64_to_image, image_to_b64, create_grid_image, superimpose_images

router = Router.from_env()
console = Console()


class SemanticDesktop(Tool):
    """A semantic desktop replaces click actions with semantic description rather than coordinates"""

    def __init__(
        self, task: Task, desktop: Desktop, data_path: str = "./.data"
    ) -> None:
        """
        Initialize and open a URL in the application.

        Args:
            task: Agent task. Defaults to None.
            desktop: Desktop instance to wrap.
            data_path (str, optional): Path to data. Defaults to "./.data".
        """
        super().__init__(wraps=desktop)
        self.desktop = desktop

        self.data_path = data_path
        self.img_path = os.path.join(self.data_path, "images", task.id)
        os.makedirs(self.img_path, exist_ok=True)

        self.task = task

    @action
    def click_object(self, description: str, type: str) -> None:
        """Click on an object on the screen

        Args:
            description (str): The description of the object including its general location, for example
                "a round dark blue icon with the text 'Home' in the top-right of the image", please be a generic as possible
            type (str): Type of click, can be 'single' for a single click or
                'double' for a double click. If you need to launch an application from the desktop choose 'double'
        """

        if type != "single" and type != "double":
            raise ValueError("type must be'single' or 'double'")

        coords = self._ocr_based_click(description, type)
        if coords is None:
            coords = self._grid_based_click(description, type)
        
        click_x = coords["x"]
        click_y = coords["y"]

        self.task.post_message(
            role="assistant",
            msg=f"Clicking coordinates {click_x}, {click_y}",
            thread="debug",
        )
        self._click_coords(x=click_x, y=click_y, type=type)
        return

    def _ocr_based_click(self, description: str, type: str) -> dict:
        # We'll try to use OCR when there is some text in the description
        # of the next step (e.g. "Click on 'Search' button")
        if '\'' in description:
            obj = description.split('\'')[1]
        elif '\"' in description:
            obj = description.split('\"')[1]
        else:
            return None
        
        click_hash = hashlib.md5(description.encode()).hexdigest()[:5]

        current_img_b64 = self.desktop.take_screenshot()
        current_img = b64_to_image(current_img_b64)

        self.task.post_message(
            role="assistant",
            msg=f"Clicking '{type}' on object '{description}'",
            thread="debug",
            images=[image_to_b64(current_img)],
        )
        self.task.post_message(
            role="assistant",
            msg=f"Looking for '{obj}' with OCR",
            thread="debug",
            images=[image_to_b64(current_img)],
        )

        image_path = os.path.join(self.img_path, f"{click_hash}_current.png")
        current_img.save(image_path)

        screenshot_b64 = image_to_b64(current_img)
        self.task.post_message(
            role="assistant",
            msg=f"Current image",
            thread="debug",
            images=[screenshot_b64],
        )

        boxes = find_boxes_with_text(image_path, obj)
        if len(boxes) == 0:
            self.task.post_message(
                role="assistant",
                msg=f"Didn't find any '{obj}' with OCR",
                thread="debug",
                images=[image_to_b64(current_img)],
            )
            return None
        
        boxes_path = os.path.join(self.img_path, f"{click_hash}_boxes.png")
        draw_bbs(boxes, image_path, boxes_path)     
        self.task.post_message(
            role="assistant",
            msg=f"Found boxes",
            thread="debug",
            images=[image_to_b64(Image.open(boxes_path))],
        )

        selected_box = boxes[0]
        return {
            "x": selected_box["x"] + selected_box["w"] // 2,
            "y": selected_box["y"] + selected_box["h"] // 2
        }


    def _grid_based_click(self, description: str, type: str) -> dict:
        color_number = os.getenv("COLOR_NUMBER", "yellow")
        color_circle = os.getenv("COLOR_CIRCLE", "red")

        click_hash = hashlib.md5(description.encode()).hexdigest()[:5]

        class ZoomSelection(BaseModel):
            """Zoom selection model"""

            number: int = Field(
                ...,
                description=f"Number of the dot closest to the place we want to click.",
            )

        current_img_b64 = self.desktop.take_screenshot()
        current_img = b64_to_image(current_img_b64)
        img_width, img_height = current_img.size

        # number of "cells" along one side; the numbers are in the corners of those "cells"
        n = 10

        thread = RoleThread()

        prompt = f"""
        You are an experienced AI trained to find the elements on the screen.
        You see a screenshot of the web application. 
        I have drawn some big {color_number} numbers on {color_circle} circles on this image 
        to help you to find required elements.
        Please tell me the closest big {color_number} number on a {color_circle} circle to the center of the {description}.
        Please note that some circles may lay on the {description}. If that's the case, return the number in any of these circles.
        Please return you response as raw JSON following the schema {ZoomSelection.model_json_schema()}
        Be concise and only return the raw json, for example if the circle you wanted to select had a number 3 in it
        you would return {{"number": 3}}
        """

        self.task.post_message(
            role="assistant",
            msg=f"Clicking '{type}' on object '{description}'",
            thread="debug",
            images=[image_to_b64(current_img)],
        )

        image_path = os.path.join(self.img_path, f"{click_hash}_current.png")
        current_img.save(image_path)
        img_width, img_height = current_img.size

        screenshot_b64 = image_to_b64(current_img)
        self.task.post_message(
            role="assistant",
            msg=f"Current image",
            thread="debug",
            images=[screenshot_b64],
        )

        grid_path = os.path.join(self.img_path, f"{click_hash}_grid.png")
        create_grid_image(
            img_width, img_height, color_circle, color_number, n, grid_path
        )

        merged_image_path = os.path.join(
            self.img_path, f"{click_hash}_merge.png"
        )
        merged_image = superimpose_images(image_path, grid_path, 1)
        merged_image.save(merged_image_path)

        merged_image_b64 = image_to_b64(merged_image)
        self.task.post_message(
            role="assistant",
            msg=f"Merged image",
            thread="debug",
            images=[merged_image_b64],
        )

        msg = RoleMessage(
            role="user",
            text=prompt,
            images=[merged_image_b64],
        )
        thread.add_msg(msg)

        response = router.chat(
            thread, namespace="zoom", expect=ZoomSelection, agent_id="SurfHamster", retries=1
        )
        if not response.parsed:
            raise SystemError("No response parsed from zoom")
        
        self.task.add_prompt(response.prompt)

        zoom_resp = response.parsed
        self.task.post_message(
            role="assistant",
            msg=f"Selection {zoom_resp.model_dump_json()}",
            thread="debug",
        )
        console.print(JSON(zoom_resp.model_dump_json()))
        chosen_number = zoom_resp.number

        # We convert the chosen number into screen coordinates
        # of the corresponding dot on the grid
        x_cell = (chosen_number - 1) // (n - 1) + 1
        y_cell = (chosen_number - 1) % (n - 1) + 1
        cell_width = img_width // n
        cell_height = img_height // n
        click_x = x_cell * cell_width
        click_y = y_cell * cell_height

        return {
            "x": click_x, 
            "y": click_y
        }


    def _click_coords(self, x: int, y: int, type: str = "single") -> None:
        """Click mouse button

        Args:
            x (Optional[int], optional): X coordinate to move to, if not provided
                it will click on current location. Defaults to None.
            y (Optional[int], optional): Y coordinate to move to, if not provided
                it will click on current location. Defaults to None.
            button (str, optional): Button to click. Defaults to "left".
        """
        body = {"x": int(x), "y": int(y)}
        resp = requests.post(f"{self.desktop.base_url}/move_mouse", json=body)
        resp.raise_for_status()
        time.sleep(2)

        if type == "single":
            resp = requests.post(f"{self.desktop.base_url}/click", json={})
            resp.raise_for_status()
            time.sleep(2)
        elif type == "double":
            resp = requests.post(f"{self.desktop.base_url}/double_click", json={})
            resp.raise_for_status()
            time.sleep(2)
        else:
            raise ValueError(f"unkown click type {type}")
        return
