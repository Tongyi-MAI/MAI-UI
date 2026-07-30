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

"""
MAI Grounding Agent - A GUI grounding agent for locating UI elements.

This module provides the MAIGroundingAgent class that uses vision-language models
to locate UI elements based on natural language instructions.
"""

import json
import re
from io import BytesIO
from typing import Any, Dict, Optional, Tuple, Union

from openai import OpenAI
from PIL import Image

from prompt import MAI_MOBILE_SYS_PROMPT_GROUNDING
from utils import pil_to_base64, safe_pil_to_bytes


# Constants
SCALE_FACTOR = 999


def parse_grounding_response(text: str) -> Dict[str, Any]:
    """
    Parse model output text containing grounding_think and answer tags.

    Args:
        text: Raw model output containing <grounding_think> and <answer> tags.

    Returns:
        Dictionary with keys:
            - "thinking": The model's reasoning process
            - "coordinate": Normalized [x, y] coordinate

    Raises:
        ValueError: If parsing fails or JSON is invalid.
    """
    text = text.strip()

    result: Dict[str, Any] = {
        "thinking": None,
        "coordinate": None,
    }

    # Extract thinking content
    think_pattern = r"<grounding_think>(.*?)</grounding_think>"
    think_match = re.search(think_pattern, text, re.DOTALL)
    if think_match:
        result["thinking"] = think_match.group(1).strip()

    # Extract answer content
    answer_pattern = r"<answer>(.*?)</answer>"
    answer_match = re.search(answer_pattern, text, re.DOTALL)
    if answer_match:
        answer_text = answer_match.group(1).strip()
        try:
            answer_json = json.loads(answer_text)
            coordinates = answer_json.get("coordinate", [])
            if len(coordinates) == 2:
                # Normalize coordinates from SCALE_FACTOR range to [0, 1]
                point_x = coordinates[0] / SCALE_FACTOR
                point_y = coordinates[1] / SCALE_FACTOR
                result["coordinate"] = [point_x, point_y]
            else:
                raise ValueError(
                    f"Invalid coordinate format: expected 2 values, got {len(coordinates)}"
                )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in answer: {e}")

    return result


class MAIGroundingAgent:
    """
    GUI grounding agent using vision-language models.

    This agent processes a screenshot and natural language instruction to
    locate a specific UI element and return its coordinates.

    Attributes:
        llm_base_url: Base URL for the LLM API endpoint.
        model_name: Name of the model to use for predictions.
        runtime_conf: Configuration dictionary for runtime parameters.
    """

    def __init__(
        self,
        llm_base_url: str,
        model_name: str,
        runtime_conf: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the MAIGroundingAgent.

        Args:
            llm_base_url: Base URL for the LLM API endpoint.
            model_name: Name of the model to use.
            runtime_conf: Optional configuration dictionary with keys:
                - max_pixels: Maximum pixels for image processing
                - min_pixels: Minimum pixels for image processing
                - temperature: Sampling temperature (default: 0.0)
                - top_k: Top-k sampling parameter (default: -1)
                - top_p: Top-p sampling parameter (default: 1.0)
                - max_tokens: Maximum tokens in response (default: 2048)
        """
        # Set default configuration
        default_conf = {
            "temperature": 0.0,
            "top_k": -1,
            "top_p": 1.0,
            "max_tokens": 2048,
        }
        self.runtime_conf = {**default_conf, **(runtime_conf or {})}

        self.llm_base_url = llm_base_url
        self.model_name = model_name
        self.llm = OpenAI(
            base_url=self.llm_base_url,
            api_key="empty",
        )

        # Extract frequently used config values
        self.temperature = self.runtime_conf["temperature"]
        self.top_k = self.runtime_conf["top_k"]
        self.top_p = self.runtime_conf["top_p"]
        self.max_tokens = self.runtime_conf["max_tokens"]

    @property
    def system_prompt(self) -> str:
        """Return the system prompt for grounding tasks."""
        return MAI_MOBILE_SYS_PROMPT_GROUNDING

    def _build_messages(
        self,
        instruction: str,
        image: Image.Image,
    ) -> list:
        """
        Build the message list for the LLM API call.

        Args:
            instruction: Grounding instruction from user.
            image: PIL Image of the screenshot.
            magic_prompt: Whether to use the magic prompt format.

        Returns:
            List of message dictionaries for the API.
        """
        encoded_string = pil_to_base64(image)

        messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": self.system_prompt,
                    }
                ],
            }
        ]

        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": instruction + "\n",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{encoded_string}"
                        },
                    },
                ],
            }
        )

        return messages

    def predict(
        self,
        instruction: str,
        image: Union[Image.Image, bytes],
        **kwargs: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Predict the coordinate of the UI element based on the instruction.

        Args:
            instruction: Grounding instruction describing the UI element to locate.
            image: PIL Image or bytes of the screenshot.
            **kwargs: Additional arguments (unused).

        Returns:
            Tuple of (prediction_text, result_dict) where:
                - prediction_text: Raw model response or error message
                - result_dict: Dictionary containing:
                    - "thinking": Model's reasoning process
                    - "coordinate": Normalized [x, y] coordinate
        """
        # Convert bytes to PIL Image if necessary
        if isinstance(image, bytes):
            image = Image.open(BytesIO(image))

        if image.mode != "RGB":
            image = image.convert("RGB")

        # Build messages
        messages = self._build_messages(instruction, image)

        # Make API call with retry logic
        max_retries = 3
        prediction = None
        result = None

        for attempt in range(max_retries):
            try:
                response = self.llm.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    frequency_penalty=0.0,
                    presence_penalty=0.0,
                    extra_body={"repetition_penalty": 1.0, "top_k": self.top_k},
                    seed=42,
                )
                prediction = response.choices[0].message.content.strip()
                print(f"Raw response:\n{prediction}")

                # Parse response
                result = parse_grounding_response(prediction)
                print(f"Parsed result:\n{result}")
                break

            except Exception as e:
                print(f"Error on attempt {attempt + 1}: {e}")
                prediction = None
                result = None

        # Return error if all retries failed
        if prediction is None or result is None:
            print("Max retry attempts reached, returning error flag.")
            return "llm client error", {"thinking": None, "coordinate": None}

        return prediction, result

