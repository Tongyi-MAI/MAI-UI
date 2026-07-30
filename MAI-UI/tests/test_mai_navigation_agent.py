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
Unit tests for MAIUINaivigationAgent._build_messages functionality.
"""

import base64
import json
import os
import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mai_naivigation_agent import MAIUINaivigationAgent, mask_image_urls_for_logging
from unified_memory import TrajMemory, TrajStep


# Create output directory for dumped messages
OUTPUT_DIR = Path(__file__).parent / "output_messages"
OUTPUT_DIR.mkdir(exist_ok=True)


def create_dummy_image(width=100, height=100, color=(255, 0, 0)):
    """Create a dummy PIL Image for testing."""
    img = Image.new("RGB", (width, height), color)
    return img


def image_to_bytes(img):
    """Convert PIL Image to bytes."""
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def dump_messages_to_file(messages, test_name):
    """
    Dump messages to a JSON file for inspection.
    
    Args:
        messages: List of message dictionaries to dump.
        test_name: Name of the test case (used for filename).
    """
    # Mask image URLs for readability
    messages_masked = mask_image_urls_for_logging(messages)
    
    output_file = OUTPUT_DIR / f"{test_name}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(messages_masked, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Messages dumped to: {output_file}")
    return output_file


class TestBuildMessages:
    """Test cases for _build_messages method."""

    @pytest.fixture
    def agent(self):
        """Create a MAIUINaivigationAgent instance for testing."""
        with patch('mai_naivigation_agent.OpenAI'):
            agent = MAIUINaivigationAgent(
                llm_base_url="http://test.com",
                model_name="test-model",
                runtime_conf={"history_n": 3}
            )
            # Initialize trajectory memory (history_images is computed from steps)
            agent.traj_memory = TrajMemory(task_goal="", task_id="test_task")
            return agent

    def test_build_messages_no_history(self, agent):
        """Test building messages without any history."""
        instruction = "Open the settings app"
        images = [create_dummy_image(color=(255, 0, 0))]

        messages = agent._build_messages(instruction, images)
        
        # Dump messages to file for inspection
        dump_messages_to_file(messages, "test_build_messages_no_history")

        # Should have system prompt, user instruction, and current image
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"][0]["text"] == instruction
        assert messages[2]["role"] == "user"
        assert "image_url" in messages[2]["content"][0]

    def test_build_messages_with_single_history(self, agent):
        """Test building messages with one history step."""
        instruction = "Click the WiFi button"
        
        # Add one history step
        step1 = TrajStep(
            screenshot=create_dummy_image(color=(255, 0, 0)),
            accessibility_tree=None,
            prediction="<thinking>Opening settings</thinking><tool_call>{...}</tool_call>",
            action={"action": "click", "coordinate": [0.5, 0.5]},
            conclusion="",
            thought="Opening settings",
            step_index=0,
            agent_type="MAIMobileAgent",
            model_name="test-model",
            screenshot_bytes=image_to_bytes(create_dummy_image(color=(255, 0, 0))),
            structured_action={"action_json": {"action": "click", "coordinate": [0.5, 0.5]}}
        )
        agent.traj_memory.steps.append(step1)
        agent.traj_memory.task_goal = instruction

        images = [
            create_dummy_image(color=(255, 0, 0)),  # history image
            create_dummy_image(color=(0, 255, 0))   # current image
        ]

        messages = agent._build_messages(instruction, images)
        
        # Dump messages to file for inspection
        dump_messages_to_file(messages, "test_build_messages_with_single_history")

        # Should have: system, user instruction, history image, history response, current image
        assert len(messages) == 5
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "user"  # history image
        assert "image_url" in messages[2]["content"][0]
        assert messages[3]["role"] == "assistant"  # history response
        assert messages[4]["role"] == "user"  # current image
        assert "image_url" in messages[4]["content"][0]

    def test_build_messages_with_multiple_history(self, agent):
        """Test building messages with multiple history steps."""
        instruction = "Type 'hello'"
        
        # Add three history steps
        for i in range(3):
            step = TrajStep(
                screenshot=create_dummy_image(color=(i*80, 0, 0)),
                accessibility_tree=None,
                prediction=f"<thinking>Step {i}</thinking><tool_call>{{...}}</tool_call>",
                action={"action": "click", "coordinate": [0.5, 0.5]},
                conclusion="",
                thought=f"Step {i}",
                step_index=i,
                agent_type="MAIMobileAgent",
                model_name="test-model",
                screenshot_bytes=image_to_bytes(create_dummy_image(color=(i*80, 0, 0))),
                structured_action={"action_json": {"action": "click", "coordinate": [0.5, 0.5]}}
            )
            agent.traj_memory.steps.append(step)
        
        agent.traj_memory.task_goal = instruction

        # history_n = 3, so we should have images for last 2 history + 1 current
        images = [
            create_dummy_image(color=(80, 0, 0)),   # history step 1
            create_dummy_image(color=(160, 0, 0)),  # history step 2
            create_dummy_image(color=(0, 255, 0))   # current image
        ]

        messages = agent._build_messages(instruction, images)
        
        # Dump messages to file for inspection
        dump_messages_to_file(messages, "test_build_messages_with_multiple_history")

        # Count image messages
        image_count = sum(1 for msg in messages if msg["role"] == "user" and 
                         any("image_url" in c for c in msg["content"] if isinstance(c, dict)))
        
        # Should have 3 images (2 from history_n-1 + 1 current)
        assert image_count == 3

    def test_build_messages_with_5_history_steps(self, agent):
        """Test building messages with 5 complete history steps showing full conversation flow."""
        instruction = "Complete the multi-step task"
        
        # Add 5 history steps with varied actions
        actions_data = [
            {"action": "open", "text": "Settings", "thought": "Opening Settings app to start the task"},
            {"action": "click", "coordinate": [0.3, 0.4], "thought": "Clicking on Network settings"},
            {"action": "swipe", "direction": "down", "thought": "Scrolling down to find WiFi option"},
            {"action": "click", "coordinate": [0.5, 0.6], "thought": "Selecting WiFi configuration"},
            {"action": "type", "text": "MyNetwork", "thought": "Typing the network name"},
        ]
        
        for i, action_data in enumerate(actions_data):
            action_json = {k: v for k, v in action_data.items() if k != "thought"}
            step = TrajStep(
                screenshot=create_dummy_image(color=(i*40, i*30, i*20)),
                accessibility_tree=None,
                prediction=f"<thinking>{action_data['thought']}</thinking><tool_call>{{...}}</tool_call>",
                action=action_json,
                conclusion="",
                thought=action_data["thought"],
                step_index=i,
                agent_type="MAIMobileAgent",
                model_name="test-model",
                screenshot_bytes=image_to_bytes(create_dummy_image(color=(i*40, i*30, i*20))),
                structured_action={"action_json": action_json}
            )
            agent.traj_memory.steps.append(step)
        
        agent.traj_memory.task_goal = instruction

        # history_n = 3, so we should have images for last 2 history + 1 current
        # That means we provide images for steps 3, 4, and current
        images = [
            create_dummy_image(color=(120, 90, 60)),   # step 3
            create_dummy_image(color=(160, 120, 80)),  # step 4
            create_dummy_image(color=(0, 255, 0))      # current image
        ]

        messages = agent._build_messages(instruction, images)
        
        # Dump messages to file for inspection
        dump_messages_to_file(messages, "test_build_messages_with_5_history_steps")

        # Verify structure
        # Count total messages
        total_messages = len(messages)
        
        # Count assistant messages (should be 5, one for each history step)
        assistant_count = sum(1 for msg in messages if msg["role"] == "assistant")
        assert assistant_count == 5, f"Expected 5 assistant messages, got {assistant_count}"
        
        # Count image messages (should be 3: last 2 history + 1 current)
        image_count = sum(1 for msg in messages if msg["role"] == "user" and 
                         any("image_url" in c for c in msg["content"] if isinstance(c, dict)))
        assert image_count == 3, f"Expected 3 image messages, got {image_count}"
        
        # Verify all 5 different thoughts are present
        all_thoughts = ["Opening Settings app", "Clicking on Network settings", 
                       "Scrolling down to find WiFi", "Selecting WiFi configuration",
                       "Typing the network name"]
        
        message_text = json.dumps(messages)
        for thought in all_thoughts:
            assert thought in message_text, f"Thought '{thought}' not found in messages"

    def test_build_messages_with_5_steps_ask_user_and_mcp(self):
        """Test building messages with 5 history steps including ask_user and MCP responses."""
        instruction = "Book a restaurant and get weather info"
        
        # Create agent with MCP tools
        mcp_tools = [
            {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"}
                    }
                }
            },
            {
                "name": "search_restaurant",
                "description": "Search for restaurants",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cuisine": {"type": "string", "description": "Type of cuisine"}
                    }
                }
            }
        ]
        
        with patch('mai_naivigation_agent.OpenAI'):
            agent = MAIUINaivigationAgent(
                llm_base_url="http://test.com",
                model_name="test-model",
                runtime_conf={"history_n": 3},
                mcp_tools=mcp_tools
            )
            agent.traj_memory = TrajMemory(task_goal="", task_id="test_task")
        
        # Define 5 steps with mixed ask_user and MCP responses
        steps_data = [
            {
                "action": {"action": "open", "text": "Chrome"},
                "thought": "Opening Chrome to search for restaurants",
                "ask_user_response": None,
                "mcp_response": None
            },
            {
                "action": {"action": "ask_user", "text": "What type of cuisine do you prefer?"},
                "thought": "Need to know user's cuisine preference",
                "ask_user_response": "I prefer Italian cuisine",
                "mcp_response": None
            },
            {
                "action": {"action": "mcp_tool", "tool_name": "search_restaurant", "cuisine": "Italian"},
                "thought": "Searching for Italian restaurants using MCP tool",
                "ask_user_response": None,
                "mcp_response": "Found 3 Italian restaurants: La Pasta, Pizza Roma, Trattoria"
            },
            {
                "action": {"action": "ask_user", "text": "Which city should I check the weather for?"},
                "thought": "Need location for weather info",
                "ask_user_response": "Check weather in San Francisco",
                "mcp_response": None
            },
            {
                "action": {"action": "mcp_tool", "tool_name": "get_weather", "location": "San Francisco"},
                "thought": "Getting weather information for San Francisco",
                "ask_user_response": None,
                "mcp_response": "Weather in San Francisco: Partly cloudy, 18°C, Wind: 15 km/h"
            }
        ]
        
        for i, step_data in enumerate(steps_data):
            step = TrajStep(
                screenshot=create_dummy_image(color=(i*50, i*40, 100)),
                accessibility_tree=None,
                prediction=f"<thinking>{step_data['thought']}</thinking><tool_call>{{...}}</tool_call>",
                action=step_data["action"],
                conclusion="",
                thought=step_data["thought"],
                step_index=i,
                agent_type="MAIMobileAgent",
                model_name="test-model",
                screenshot_bytes=image_to_bytes(create_dummy_image(color=(i*50, i*40, 100))),
                structured_action={"action_json": step_data["action"]},
                ask_user_response=step_data["ask_user_response"],
                mcp_response=step_data["mcp_response"]
            )
            agent.traj_memory.steps.append(step)
        
        agent.traj_memory.task_goal = instruction

        # history_n = 3, so we provide images for last 2 history + 1 current
        images = [
            create_dummy_image(color=(150, 120, 100)),  # step 3
            create_dummy_image(color=(200, 160, 100)),  # step 4
            create_dummy_image(color=(0, 255, 0))       # current image
        ]

        messages = agent._build_messages(instruction, images)
        
        # Dump messages to file for inspection
        dump_messages_to_file(messages, "test_build_messages_with_5_steps_ask_user_and_mcp")

        # Verify structure
        # Count assistant messages (should be 5)
        assistant_count = sum(1 for msg in messages if msg["role"] == "assistant")
        assert assistant_count == 5, f"Expected 5 assistant messages, got {assistant_count}"
        
        # Count image messages (should be 3: last 2 history + 1 current)
        image_count = sum(1 for msg in messages if msg["role"] == "user" and 
                         any("image_url" in c for c in msg["content"] if isinstance(c, dict)))
        assert image_count == 3, f"Expected 3 image messages, got {image_count}"
        
        # Verify ask_user_response is present
        message_text = json.dumps(messages)
        assert "I prefer Italian cuisine" in message_text, "ask_user_response 1 not found"
        assert "Check weather in San Francisco" in message_text, "ask_user_response 2 not found"
        
        # Verify mcp_response is present
        assert "Found 3 Italian restaurants" in message_text, "mcp_response 1 not found"
        assert "Weather in San Francisco" in message_text, "mcp_response 2 not found"
        
        # Verify MCP tools are in system prompt
        system_content = messages[0]["content"][0]["text"]
        assert "get_weather" in system_content, "MCP tool get_weather not in system prompt"
        assert "search_restaurant" in system_content, "MCP tool search_restaurant not in system prompt"
        
        # Count user text messages (not images): should include ask_user and mcp responses
        user_text_messages = [msg for msg in messages 
                              if msg["role"] == "user" 
                              and msg["content"][0].get("type") == "text"]
        
        # We should have at least: instruction + 2 ask_user_responses + 2 mcp_responses = 5
        # But instruction is part of the initial user message
        # So we expect: 1 (instruction) + 4 (responses) = at least 4 user text messages
        assert len(user_text_messages) >= 4, f"Expected at least 4 user text messages, got {len(user_text_messages)}"

    def test_build_messages_with_ask_user_response(self, agent):
        """Test building messages with ask_user_response."""
        instruction = "Complete the form"
        
        step = TrajStep(
            screenshot=create_dummy_image(color=(255, 0, 0)),
            accessibility_tree=None,
            prediction="<thinking>Need user input</thinking><tool_call>{...}</tool_call>",
            action={"action": "ask_user", "text": "What's your name?"},
            conclusion="",
            thought="Need user input",
            step_index=0,
            agent_type="MAIMobileAgent",
            model_name="test-model",
            screenshot_bytes=image_to_bytes(create_dummy_image(color=(255, 0, 0))),
            structured_action={"action_json": {"action": "ask_user", "text": "What's your name?"}},
            ask_user_response="My name is Alice"
        )
        agent.traj_memory.steps.append(step)
        agent.traj_memory.task_goal = instruction

        images = [
            create_dummy_image(color=(255, 0, 0)),
            create_dummy_image(color=(0, 255, 0))
        ]

        messages = agent._build_messages(instruction, images)
        
        # Dump messages to file for inspection
        dump_messages_to_file(messages, "test_build_messages_with_ask_user_response")

        # Should include ask_user_response
        user_response_found = False
        for msg in messages:
            if msg["role"] == "user" and msg["content"][0].get("type") == "text":
                if msg["content"][0]["text"] == "My name is Alice":
                    user_response_found = True
                    break
        
        assert user_response_found

    def test_build_messages_with_mcp_response(self):
        """Test building messages with mcp_response and MCP tools configured."""
        instruction = "Get the current weather"
        
        # Create agent with MCP tools
        mcp_tools = [
            {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name"
                        }
                    }
                }
            }
        ]
        
        with patch('mai_naivigation_agent.OpenAI'):
            agent = MAIUINaivigationAgent(
                llm_base_url="http://test.com",
                model_name="test-model",
                runtime_conf={"history_n": 3},
                mcp_tools=mcp_tools
            )
            agent.traj_memory = TrajMemory(task_goal="", task_id="test_task")
        
        step = TrajStep(
            screenshot=create_dummy_image(color=(255, 0, 0)),
            accessibility_tree=None,
            prediction="<thinking>Getting weather</thinking><tool_call>{...}</tool_call>",
            action={"action": "mcp_tool", "tool_name": "get_weather"},
            conclusion="",
            thought="Getting weather",
            step_index=0,
            agent_type="MAIMobileAgent",
            model_name="test-model",
            screenshot_bytes=image_to_bytes(create_dummy_image(color=(255, 0, 0))),
            structured_action={"action_json": {"action": "mcp_tool", "tool_name": "get_weather"}},
            mcp_response="Weather: Sunny, 25°C"
        )
        agent.traj_memory.steps.append(step)
        agent.traj_memory.task_goal = instruction

        images = [
            create_dummy_image(color=(255, 0, 0)),
            create_dummy_image(color=(0, 255, 0))
        ]

        messages = agent._build_messages(instruction, images)
        
        # Dump messages to file for inspection
        dump_messages_to_file(messages, "test_build_messages_with_mcp_response")

        # Should include mcp_response
        mcp_response_found = False
        for msg in messages:
            if msg["role"] == "user" and msg["content"][0].get("type") == "text":
                if msg["content"][0]["text"] == "Weather: Sunny, 25°C":
                    mcp_response_found = True
                    break
        
        assert mcp_response_found
        
        # System prompt should contain MCP tool information
        system_content = messages[0]["content"][0]["text"]
        assert "get_weather" in system_content

    def test_build_messages_system_prompt(self, agent):
        """Test that system prompt is correctly included."""
        instruction = "Test instruction"
        images = [create_dummy_image()]

        messages = agent._build_messages(instruction, images)

        assert messages[0]["role"] == "system"
        assert len(messages[0]["content"]) > 0
        assert messages[0]["content"][0]["type"] == "text"
        assert len(messages[0]["content"][0]["text"]) > 0

    def test_build_messages_with_mcp_tools(self):
        """Test system prompt includes MCP tools when configured."""
        mcp_tools = [
            {
                "name": "get_weather",
                "description": "Get current weather",
                "parameters": {"type": "object", "properties": {}}
            }
        ]
        
        with patch('mai_naivigation_agent.OpenAI'):
            agent = MAIUINaivigationAgent(
                llm_base_url="http://test.com",
                model_name="test-model",
                runtime_conf={"history_n": 3},
                mcp_tools=mcp_tools
            )
            agent.traj_memory = TrajMemory(task_goal="", task_id="test_task")

        instruction = "Test with MCP"
        images = [create_dummy_image()]

        messages = agent._build_messages(instruction, images)
        
        # Dump messages to file for inspection
        dump_messages_to_file(messages, "test_build_messages_with_mcp_tools")

        # System prompt should contain tool information
        system_content = messages[0]["content"][0]["text"]
        assert "get_weather" in system_content

    def test_build_messages_image_encoding(self, agent):
        """Test that images are properly base64 encoded."""
        instruction = "Test image encoding"
        images = [create_dummy_image(color=(123, 45, 67))]

        messages = agent._build_messages(instruction, images)

        # Find the image message
        image_msg = None
        for msg in messages:
            if msg["role"] == "user" and "image_url" in msg["content"][0]:
                image_msg = msg
                break

        assert image_msg is not None
        image_url = image_msg["content"][0]["image_url"]["url"]
        assert image_url.startswith("data:image/png;base64,")
        
        # Verify it's valid base64
        base64_data = image_url.split(",")[1]
        try:
            decoded = base64.b64decode(base64_data)
            assert len(decoded) > 0
        except Exception as e:
            pytest.fail(f"Invalid base64 encoding: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

