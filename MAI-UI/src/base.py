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

"""Base agent class for mobile GUI automation agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from unified_memory import TrajMemory, TrajStep


class BaseAgent(ABC):
    """
    Abstract base class for all GUI automation agents.

    This class provides common functionality for trajectory management
    and defines the interface that all agents must implement.
    """

    def __init__(self) -> None:
        """Initialize the base agent with empty trajectory memory."""
        self.traj_memory = TrajMemory(
            task_goal="",
            task_id="",
            steps=[],
        )

    @property
    def thoughts(self) -> List[str]:
        """Return list of thoughts from trajectory memory."""
        return [step.thought if step.thought else "" for step in self.traj_memory.steps]

    @property
    def actions(self) -> List[Dict[str, Any]]:
        """Return list of actions from trajectory memory."""
        return [step.action for step in self.traj_memory.steps]

    @property
    def conclusions(self) -> List[str]:
        """Return list of conclusions from trajectory memory."""
        return [step.conclusion for step in self.traj_memory.steps]

    @property
    def observations(self) -> List[Dict[str, Any]]:
        """Return list of observations from trajectory memory."""
        return [
            {
                "screenshot": step.screenshot_bytes,
                "accessibility_tree": step.accessibility_tree,
            }
            for step in self.traj_memory.steps
        ]

    @property
    def history_images(self) -> List[bytes]:
        """Return list of screenshot bytes from trajectory memory."""
        return [step.screenshot_bytes for step in self.traj_memory.steps]

    @property
    def history_responses(self) -> List[str]:
        """Return list of predictions from trajectory memory."""
        return [step.prediction for step in self.traj_memory.steps]

    @abstractmethod
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
            obs: Current observation containing screenshot and optional accessibility tree.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple of (prediction_text, action_dict).
        """
        pass

    def reset(self) -> None:
        """Reset the trajectory memory for a new task."""
        self.traj_memory = TrajMemory(
            task_goal="",
            task_id="",
            steps=[],
        )

    def load_traj(self, traj_memory: TrajMemory) -> None:
        """
        Load trajectory from existing TrajMemory object.

        Args:
            traj_memory: TrajMemory object containing trajectory data.
        """
        self.traj_memory = traj_memory

    def save_traj(self) -> Dict[str, Any]:
        """
        Save current trajectory to a dictionary format.

        Returns:
            Dictionary containing the trajectory data that can be serialized.
        """
        steps_data = []
        for step in self.traj_memory.steps:
            step_dict = {
                "screenshot_bytes": step.screenshot_bytes,
                "accessibility_tree": step.accessibility_tree,
                "prediction": step.prediction,
                "action": step.action,
                "conclusion": step.conclusion,
                "thought": step.thought,
                "step_index": step.step_index,
                "agent_type": step.agent_type,
                "model_name": step.model_name,
            }
            steps_data.append(step_dict)

        return {
            "task_goal": self.traj_memory.task_goal,
            "task_id": self.traj_memory.task_id,
            "steps": steps_data,
        }
