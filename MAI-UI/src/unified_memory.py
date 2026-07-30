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

"""Unified memory structures for trajectory tracking."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from PIL import Image


@dataclass
class TrajStep:
    """
    Represents a single step in an agent's trajectory.

    Attributes:
        screenshot: PIL Image of the screen at this step.
        accessibility_tree: Accessibility tree data for the screen.
        prediction: Raw model prediction/response.
        action: Parsed action dictionary.
        conclusion: Conclusion or summary of the step.
        thought: Model's reasoning/thinking process.
        step_index: Index of this step in the trajectory.
        agent_type: Type of agent that produced this step.
        model_name: Name of the model used.
        screenshot_bytes: Original screenshot as bytes (for compatibility).
        structured_action: Structured action with metadata.
    """

    screenshot: Image.Image
    accessibility_tree: Optional[Dict[str, Any]]
    prediction: str
    action: Dict[str, Any]
    conclusion: str
    thought: str
    step_index: int
    agent_type: str
    model_name: str
    screenshot_bytes: Optional[bytes] = None
    structured_action: Optional[Dict[str, Any]] = None
    ask_user_response: Optional[str] = None
    mcp_response: Optional[str] = None


@dataclass
class TrajMemory:
    """
    Container for a complete trajectory of agent steps.

    Attributes:
        task_goal: The goal/instruction for this trajectory.
        task_id: Unique identifier for the task.
        steps: List of trajectory steps.
    """

    task_goal: str
    task_id: str
    steps: List[TrajStep] = field(default_factory=list)
