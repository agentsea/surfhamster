import os
import time
import requests
from random import randint

from agentdesk.device import Desktop
from taskara import Task
from toolfuse import Tool, action


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
        info = self.desktop.info()
        screen_size = info["screen_size"]
        self._click_coords(screen_size["x"] // 2, screen_size["y"] // 2, "single")

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
