# Copyright (c) 2025, Alibaba Cloud and its affiliates;
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions for image processing and conversion."""

import base64
from io import BytesIO
from typing import Union, Optional, Tuple, Dict, Any

from PIL import Image
from PIL import ImageDraw


def safe_pil_to_bytes(image: Union[Image.Image, bytes]) -> bytes:
    if isinstance(image, Image.Image):
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="PNG")
        return img_byte_arr.getvalue()
    elif isinstance(image, bytes):
        return image
    else:
        raise TypeError(f"Expected PIL Image or bytes, got {type(image)}")

def pil_to_base64(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def save_screenshot(screenshot: Image.Image, path: str) -> None:
  screenshot.save(path)
  print(f"Screenshot saved in {path}")

def extract_click_coordinates(action: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    coordinate = action.get('coordinate')
    if coordinate is None or not coordinate:
        return None
    x = coordinate[0]
    y = coordinate[1]
    action_corr = (x, y)
    return action_corr

# Function to draw points on an image
def draw_clicks_on_image(image_path: str, click_coords: Tuple[float, float], output_path: Optional[str] = None) -> Image.Image:
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)

    # Draw each click coordinate as a red circle
    (x, y) = click_coords
    radius = 20
    if x and y:  # if get the coordinate, draw a circle
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill='red', outline='red')

    # Save the modified image
    if output_path:
        save_screenshot(image, output_path)
    return image