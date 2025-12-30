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
MAI Mobile Agent - A GUI automation agent for mobile devices.

This module provides the MAIMobileAgent class that uses vision-language models
to interact with mobile device interfaces based on natural language instructions.
"""

import copy
import json
import re
import traceback
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from openai import OpenAI
from PIL import Image

from base import BaseAgent
from prompt import MAI_MOBILE_SYS_PROMPT, MAI_MOBILE_SYS_PROMPT_ASK_USER_MCP
from unified_memory import TrajStep
from utils import pil_to_base64, safe_pil_to_bytes

# Constants
SCALE_FACTOR = 999


def mask_image_urls_for_logging(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create a copy of messages with image URLs masked for logging.

    Args:
        messages: List of message dictionaries that may contain image URLs.

    Returns:
        Deep copy of messages with image URLs replaced by "[IMAGE_DATA]".
    """
    messages_masked = copy.deepcopy(messages)
    for message in messages_masked:
        content = message.get("content", [])
        if content and isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and "image_url" in item:
                    item["image_url"]["url"] = "[IMAGE_DATA]"
    return messages_masked


def parse_tagged_text(text: str) -> Dict[str, Any]:
    """
    Parse text containing XML-style tags to extract thinking and tool_call content.

    Args:
        text: Text containing <thinking> and <tool_call> tags.

    Returns:
        Dictionary with keys:
            - "thinking": Content inside <thinking> tags (str or None)
            - "tool_call": Parsed JSON content inside <tool_call> tags (dict or None)

    Raises:
        ValueError: If tool_call content is not valid JSON.
    """
    # Handle thinking model output format (uses </think> instead of </thinking>)
    if "</think>" in text and "</thinking>" not in text:
        text = text.replace("</think>", "</thinking>")
        text = "<thinking>" + text

    # Define regex pattern with non-greedy matching
    pattern = r"<thinking>(.*?)</thinking>.*?<tool_call>(.*?)</tool_call>"

    result: Dict[str, Any] = {
        "thinking": None,
        "tool_call": None,
    }

    # Use re.DOTALL to match newlines
    match = re.search(pattern, text, re.DOTALL)
    if match:
        result = {
            "thinking": match.group(1).strip().strip('"'),
            "tool_call": match.group(2).strip().strip('"'),
        }

    # Parse tool_call as JSON
    if result["tool_call"]:
        try:
            result["tool_call"] = json.loads(result["tool_call"])
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in tool_call: {e}")

    return result


def parse_action_to_structure_output(text: str) -> Dict[str, Any]:
    """
    Parse model output text into structured action format.

    Args:
        text: Raw model output containing thinking and tool_call tags.

    Returns:
        Dictionary with keys:
            - "thinking": The model's reasoning process
            - "action_json": Parsed action with normalized coordinates

    Note:
        Coordinates are normalized to [0, 1] range by dividing by SCALE_FACTOR.
    """
    text = text.strip()

    results = parse_tagged_text(text)
    thinking = results["thinking"]
    tool_call = results["tool_call"]
    action = tool_call["arguments"]

    # Normalize coordinates from SCALE_FACTOR range to [0, 1]
    if "coordinate" in action:
        coordinates = action["coordinate"]
        if len(coordinates) == 2:
            point_x, point_y = coordinates
        elif len(coordinates) == 4:
            x1, y1, x2, y2 = coordinates
            point_x = (x1 + x2) / 2
            point_y = (y1 + y2) / 2
        else:
            raise ValueError(
                f"Invalid coordinate format: expected 2 or 4 values, got {len(coordinates)}"
            )
        point_x = point_x / SCALE_FACTOR
        point_y = point_y / SCALE_FACTOR
        action["coordinate"] = [point_x, point_y]

    return {
        "thinking": thinking,
        "action_json": action,
    }


class MAIUINaivigationAgent(BaseAgent):
    """
    Mobile automation agent using vision-language models.

    This agent processes screenshots and natural language instructions to
    generate GUI actions for mobile device automation.

    Attributes:
        llm_base_url: Base URL for the LLM API endpoint.
        model_name: Name of the model to use for predictions.
        runtime_conf: Configuration dictionary for runtime parameters.
        history_n: Number of history steps to include in context.
    """

    def __init__(
        self,
        llm_base_url: str,
        model_name: str,
        runtime_conf: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize the MAIMobileAgent.

        Args:
            llm_base_url: Base URL for the LLM API endpoint.
            model_name: Name of the model to use.
            runtime_conf: Optional configuration dictionary with keys:
                - history_n: Number of history images to include (default: 3)
                - max_pixels: Maximum pixels for image processing
                - min_pixels: Minimum pixels for image processing
                - temperature: Sampling temperature (default: 0.0)
                - top_k: Top-k sampling parameter (default: -1)
                - top_p: Top-p sampling parameter (default: 1.0)
                - max_tokens: Maximum tokens in response (default: 2048)
            tools: Optional list of MCP tool definitions. Each tool should be a dict
                with 'name', 'description', and 'parameters' keys.
        """
        super().__init__()
        
        # Store MCP tools
        self.tools = tools or []

        # Set default configuration
        default_conf = {
            "history_n": 3,
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
        self.history_n = self.runtime_conf["history_n"]

    @property
    def system_prompt(self) -> str:
        """
        Generate the system prompt based on available MCP tools.

        Returns:
            System prompt string, with MCP tools section if tools are configured.
        """
        if self.tools:
            tools_str = "\n".join(
                [json.dumps(tool, ensure_ascii=False) for tool in self.tools]
            )
            return MAI_MOBILE_SYS_PROMPT_ASK_USER_MCP.render(tools=tools_str)
        return MAI_MOBILE_SYS_PROMPT

    @property
    def history_responses(self) -> List[str]:
        """
        Generate formatted history responses for context.

        Returns:
            List of formatted response strings with thinking and tool_call tags.
        """
        history_responses = []

        for step in self.traj_memory.steps:
            thinking = step.thought
            structured_action = step.structured_action

            if not structured_action:
                continue

            action_json = copy.deepcopy(structured_action.get("action_json", {}))

            # Convert normalized coordinates back to SCALE_FACTOR range
            if "coordinate" in action_json:
                coordinates = action_json.get("coordinate", [])
                if len(coordinates) == 2:
                    point_x, point_y = coordinates
                elif len(coordinates) == 4:
                    x1, y1, x2, y2 = coordinates
                    point_x = (x1 + x2) / 2
                    point_y = (y1 + y2) / 2
                else:
                    continue
                action_json["coordinate"] = [
                    int(point_x * SCALE_FACTOR),
                    int(point_y * SCALE_FACTOR),
                ]

            tool_call_dict = {
                "name": "mobile_use",
                "arguments": action_json,
            }
            tool_call_json = json.dumps(tool_call_dict, separators=(",", ":"))
            history_responses.append(
                f"<thinking>\n{thinking}\n</thinking>\n<tool_call>\n{tool_call_json}\n</tool_call>"
            )

        return history_responses

    def _prepare_images(self, screenshot_bytes: bytes) -> List[Image.Image]:
        """
        Prepare image list including history and current screenshot.

        Args:
            screenshot_bytes: Current screenshot as bytes.

        Returns:
            List of PIL Images (history + current).
        """
        # Calculate how many history images to include
        if len(self.history_images) > 0:
            max_history = min(len(self.history_images), self.history_n - 1)
            recent_history = self.history_images[-max_history:] if max_history > 0 else []
        else:
            recent_history = []

        # Add current image bytes
        recent_history.append(screenshot_bytes)

        # Normalize input type
        if isinstance(recent_history, bytes):
            recent_history = [recent_history]
        elif isinstance(recent_history, np.ndarray):
            recent_history = list(recent_history)
        elif not isinstance(recent_history, list):
            raise TypeError(f"Unidentified images type: {type(recent_history)}")

        # Convert all images to PIL format
        images = []
        for image in recent_history:
            if isinstance(image, bytes):
                image = Image.open(BytesIO(image))
            elif isinstance(image, Image.Image):
                pass
            else:
                raise TypeError(f"Expected bytes or PIL Image, got {type(image)}")

            if image.mode != "RGB":
                image = image.convert("RGB")

            images.append(image)

        return images

    def _build_messages(
        self,
        instruction: str,
        images: List[Image.Image],
        user_feedback: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build the message list for the LLM API call.

        Args:
            instruction: Task instruction from user.
            images: List of prepared images.

        Returns:
            List of message dictionaries for the API.
        """
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": self.system_prompt}],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": instruction}],
            },
        ]

        image_num = 0
        history_responses = self.history_responses

        if len(history_responses) > 0:
            for history_idx, history_response in enumerate(history_responses):
                # Only include images for recent history (last history_n responses)
                if history_idx + self.history_n >= len(history_responses):
                    # Add image before the assistant response
                    if image_num < len(images) - 1:
                        cur_image = images[image_num]
                        encoded_string = pil_to_base64(cur_image)
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{encoded_string}"},
                            }],
                        })
                        image_num += 1

                messages.append({
                    "role": "assistant",
                    "content": [{"type": "text", "text": history_response}],
                })

            # Add current image (last one in images list)
            if image_num < len(images):
                cur_image = images[image_num]
                encoded_string = pil_to_base64(cur_image)
                content = [{
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{encoded_string}"},
                }]
                
                # Add user feedback if available
                if user_feedback:
                    content.append({
                        "type": "text",
                        "text": f"\nUser Feedback: {user_feedback}"
                    })
                
                messages.append({
                    "role": "user",
                    "content": content,
                })
        else:
            # No history, just add the current image
            cur_image = images[0]
            encoded_string = pil_to_base64(cur_image)
            content = [{
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encoded_string}"},
            }]
            
            # Add user feedback if available
            if user_feedback:
                content.append({
                    "type": "text",
                    "text": f"\nUser Feedback: {user_feedback}"
                })

            messages.append({
                "role": "user",
                "content": content,
            })

        return messages

    def predict(
        self,
        instruction: str,
        obs: Dict[str, Any],
        **kwargs: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Predict the next action based on the current observation.

        Args:
            instruction: Task instruction/goal.
            obs: Current observation containing:
                - screenshot: PIL Image or bytes of current screen
                - accessibility_tree: Optional accessibility tree data
            **kwargs: Additional arguments including:
                - extra_info: Optional extra context string

        Returns:
            Tuple of (prediction_text, action_dict) where:
                - prediction_text: Raw model response or error message
                - action_dict: Parsed action dictionary
        """
        # Set task goal if not already set
        if not self.traj_memory.task_goal:
            self.traj_memory.task_goal = instruction

        # Process screenshot
        screenshot_pil = obs["screenshot"]
        screenshot_bytes = safe_pil_to_bytes(screenshot_pil)

        # Prepare images
        images = self._prepare_images(screenshot_bytes)
        
        # Get user feedback from observation
        user_feedback = obs.get("user_feedback")

        # Build messages
        messages = self._build_messages(instruction, images, user_feedback=user_feedback)

        # Make API call with retry logic
        max_retries = 3
        prediction = None
        action_json = None

        for attempt in range(max_retries):
            try:
                messages_print = mask_image_urls_for_logging(messages)
                print(f"Messages (attempt {attempt + 1}):\n{messages_print}")

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
                parsed_response = parse_action_to_structure_output(prediction)
                thinking = parsed_response["thinking"]
                action_json = parsed_response["action_json"]
                print(f"Parsed response:\n{parsed_response}")
                break

            except Exception as e:
                print(f"Error on attempt {attempt + 1}: {e}")
                traceback.print_exc()
                prediction = None
                action_json = None

        # Return error if all retries failed
        if prediction is None or action_json is None:
            print("Max retry attempts reached, returning error flag.")
            return "llm client error", {"action": None}

        # Create and store trajectory step
        traj_step = TrajStep(
            screenshot=screenshot_pil,
            accessibility_tree=obs.get("accessibility_tree"),
            prediction=prediction,
            action=action_json,
            conclusion="",
            thought=thinking,
            step_index=len(self.traj_memory.steps),
            agent_type="MAIMobileAgent",
            model_name=self.model_name,
            screenshot_bytes=screenshot_bytes,
            structured_action={"action_json": action_json},
        )
        self.traj_memory.steps.append(traj_step)

        return prediction, action_json

    def reset(self, runtime_logger: Any = None) -> None:
        """
        Reset the trajectory memory for a new task.

        Args:
            runtime_logger: Optional logger (unused, kept for API compatibility).
        """
        super().reset()


