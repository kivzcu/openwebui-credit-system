"""
title: Context Length Filter
description: Truncate chat context length with 'token limit' and 'max turns', showing status while limit exceeded. System message and multimodal messages excluded.
author: Kejun Luo
version: 0.5
"""

import tiktoken
from pydantic import BaseModel, Field
from typing import Optional, Callable, Any, Awaitable


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=0, description="Priority level")
        max_turns: int = Field(
            default=25,
            description="Number of conversation turns to retain. Set '0' for unlimited",
        )
        token_limit: int = Field(
            default=10000,
            description="Number of token limit to retain. Set '0' for unlimited",
        )

    class UserValves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()
        self.encoding = tiktoken.get_encoding("cl100k_base")

    async def inlet(
        self,
        body: dict,
        __event_emitter__: Callable[[Any], Awaitable[None]],
        __model__: Optional[dict] = None,
    ) -> dict:
        messages = body["messages"]
        chat_messages = messages[:]

        # truncate turns
        if self.valves.max_turns > 0:
            current_turns = (len(chat_messages) - 1) // 2
            if current_turns > self.valves.max_turns:
                sent_msg_count = self.valves.max_turns * 2 + 1
                await self.show_exceeded_status(
                    __event_emitter__, self.valves.max_turns
                )
                chat_messages = chat_messages[-sent_msg_count:]

        # truncate tokens
        if self.valves.token_limit > 0:
            filter_messages = []
            current_toks = 0
            for msg in reversed(chat_messages):
                toks = self.count_tokens(msg)
                not_user = msg.get("role", "") != "user"
                # the first message must be a user message, so a user message should not be truncated.
                if (current_toks + toks > self.valves.token_limit) and not_user:
                    current_turns = len(filter_messages) // 2 + 1
                    await self.show_exceeded_status(__event_emitter__, current_turns)
                    break
                filter_messages.insert(0, msg)
                current_toks += toks
        else:
            filter_messages = chat_messages

        body["messages"] = filter_messages

        return body

    async def show_exceeded_status(
        self, __event_emitter__: Callable[[Any], Awaitable[None]], turn_count: int
    ) -> None:
        count = turn_count * 2 + 1
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": f"Context limit reached - keeping last {count} messages",
                    "done": True,
                },
            }
        )

    def count_tokens(self, msg: dict) -> int:
        content = msg.get("content", "")
        total_tokens = 0

        if isinstance(content, list):
            # Handle multi-modal content
            for item in content:
                if item.get("type") == "text":
                    text = item.get("text", "")
                    total_tokens += len(self.encoding.encode(text))
        elif isinstance(content, str):
            # Handle text-only content
            total_tokens = len(self.encoding.encode(content))
        else:
            # Handle unexpected content types
            total_tokens = 0

        return total_tokens
