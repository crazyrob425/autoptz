"""
AI Controller for Setup Wizard

Uses Claude API to drive the camera setup process through MCP tool calls.
"""

import json
import logging
from typing import Optional, Dict, List, Any, Callable
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AIWizardMessage:
    """Message from AI during wizard"""
    role: str  # "assistant" or "user"
    content: str
    tool_calls: Optional[List[Dict]] = None


class WizardAIController:
    """
    Orchestrates wizard using Claude API + MCP tool calling.
    Handles conversation loop, tool execution, and state management.
    """

    def __init__(self, api_key: Optional[str] = None, mcp_server=None):
        """
        Initialize AI controller.
        
        Args:
            api_key: Anthropic API key (or read from env)
            mcp_server: MCP server instance providing tools
        """
        self.api_key = api_key or self._get_api_key()
        self.mcp_server = mcp_server
        self.conversation_history: List[Dict] = []
        self.setup_state = {
            "step": "discovery",
            "discovered_cameras": [],
            "configured_cameras": {},
        }

    def _get_api_key(self) -> str:
        """Get Anthropic API key from environment"""
        import os
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        return key

    def get_system_prompt(self) -> str:
        """Get system prompt for Claude"""
        return """You are an expert AI assistant helping users set up IP cameras for surveillance.

Your goal is to guide the user through a multi-step setup wizard:
1. Discover cameras on the network
2. Probe each camera's capabilities (PTZ, audio, events, etc.)
3. Identify any driver requirements
4. Configure detection sensitivity (face confidence, motion threshold)
5. Define trigger zones (areas of interest on the frame)
6. Test and validate the setup

Use the provided tools to:
- Scan for cameras
- Probe camera capabilities
- Identify driver needs
- Configure sensitivity
- Define trigger zones
- Test connections

Be conversational, helpful, and guide the user step-by-step. Explain what each step does and why it matters.
When you call tools, be explicit about what you're doing and why."""

    async def start_wizard_conversation(self, user_message: str = None) -> AIWizardMessage:
        """
        Start or continue wizard conversation.
        
        Args:
            user_message: Optional initial message from user
            
        Returns:
            AIWizardMessage with assistant response
        """
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

        client = Anthropic(api_key=self.api_key)

        # Build initial message if needed
        if not user_message:
            user_message = "Help me set up my IP cameras. Let's start by discovering what cameras are available on my network."

        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Get tools from MCP server
        tools = self.mcp_server.define_tools() if self.mcp_server else []

        # Call Claude with tools
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=self.get_system_prompt(),
            tools=tools if tools else None,
            messages=self.conversation_history,
        )

        # Process response
        assistant_message = {
            "role": "assistant",
            "content": "",
            "tool_calls": []
        }

        for content_block in response.content:
            if hasattr(content_block, 'text'):
                assistant_message["content"] = content_block.text
            elif hasattr(content_block, 'type') and content_block.type == "tool_use":
                assistant_message["tool_calls"].append({
                    "id": content_block.id,
                    "name": content_block.name,
                    "input": content_block.input,
                })

        # Add to history
        self.conversation_history.append(assistant_message)

        # Execute any tool calls
        if assistant_message["tool_calls"] and self.mcp_server:
            await self._execute_tool_calls(assistant_message["tool_calls"])

        return AIWizardMessage(
            role="assistant",
            content=assistant_message["content"],
            tool_calls=assistant_message["tool_calls"]
        )

    async def _execute_tool_calls(self, tool_calls: List[Dict]) -> None:
        """
        Execute tool calls and add results to conversation.
        """
        for tool_call in tool_calls:
            logger.info(f"Executing tool: {tool_call['name']}")

            # Execute tool
            result_str = self.mcp_server.handle_tool_call(
                tool_call["name"],
                tool_call.get("input", {})
            )

            # Add result to conversation
            self.conversation_history.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call["id"],
                        "content": result_str,
                    }
                ]
            })

    async def continue_conversation(self, user_message: str) -> AIWizardMessage:
        """
        Continue wizard conversation with new user message.
        
        Args:
            user_message: User's response or next step
            
        Returns:
            AIWizardMessage with assistant response
        """
        # Update state and recurse through start_wizard_conversation
        return await self.start_wizard_conversation(user_message)

    def get_setup_summary(self) -> Dict[str, Any]:
        """
        Get summary of setup progress.
        """
        if self.mcp_server:
            result_str = self.mcp_server.handle_tool_call("get_setup_progress", {})
            return json.loads(result_str)
        
        return {
            "summary": "No setup data available",
            "state": self.setup_state
        }

    def reset_wizard(self) -> None:
        """Reset wizard to initial state"""
        self.conversation_history = []
        self.setup_state = {
            "step": "discovery",
            "discovered_cameras": [],
            "configured_cameras": {},
        }

    @staticmethod
    def create_sync_wrapper(controller: 'WizardAIController'):
        """
        Create synchronous wrapper for Qt integration.
        Qt slots expect synchronous calls.
        """
        def sync_start(user_message: str = None) -> AIWizardMessage:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                controller.start_wizard_conversation(user_message)
            )

        def sync_continue(user_message: str) -> AIWizardMessage:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                controller.continue_conversation(user_message)
            )

        return {
            "start": sync_start,
            "continue": sync_continue,
            "get_summary": controller.get_setup_summary,
            "reset": controller.reset_wizard,
        }
