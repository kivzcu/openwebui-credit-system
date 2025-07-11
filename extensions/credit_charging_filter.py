"""
title: Credit management Charging credits
author: DDVVY
version: 1.0
"""

from pydantic import BaseModel, Field
import httpx

CREDITS_API_BASE_URL = "http://localhost:8000/api/credits"


class Filter:
    class Valves(BaseModel):
        show_status: bool = Field(
            default=True, description="Zobrazit info o stržení kreditů"
        )

    def __init__(self):
        self.valves = self.Valves()

    def safe_token_count(self, text: str) -> int:
        return max(1, len(text) // 4)

    def extract_token_count(self, body: dict, token_type: str) -> int:
        """
        Tries to extract prompt_tokens or completion_tokens from various places.
        Preferably from messages[-1]["usage"], then fallback to metadata, then estimate.
        """
        method_used = None
        token_count = 0

        try:
            token_count = int(body["messages"][-1]["usage"].get(token_type, 0))
            method_used = "messages[-1]['usage']"
        except Exception:
            pass

        if method_used is None:
            try:
                token_count = int(body.get("metadata", {}).get("metrics", {}).get(token_type, 0))
                method_used = "metadata.metrics"
            except Exception:
                pass

        if method_used is None:
            try:
                token_count = int(body.get(token_type, 0))
                method_used = "body[token_type]"
            except Exception:
                pass

        print(f"[extract_token_count] token_type={token_type}, token_count={token_count}, method_used={method_used}")
        return token_count
    
    async def outlet(
        self, body, __user__=None, __event_emitter__=None, __event_call__=None
    ):
        user_id = __user__.get("id")
        model_name = body.get("model", "gpt-3.5-turbo")

        prompt_tokens = self.extract_token_count(body, "prompt_tokens")
        completion_tokens = self.extract_token_count(body, "completion_tokens")

        try:
            async with httpx.AsyncClient() as client:
                model_res = await client.get(
                    f"{CREDITS_API_BASE_URL}/models"
                )
                user_res = await client.get(
                    f"{CREDITS_API_BASE_URL}/users"
                )
                model_res.raise_for_status()
                user_res.raise_for_status()
                models = model_res.json()
                users = user_res.json()
        except Exception as e:
            if self.valves.show_status and __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f" Failed to load credit metadata: {str(e)}",
                            "done": True,
                        },
                    }
                )
            return body

        model_data = next((m for m in models if m.get("id") == model_name), None)
        user_data = next((u for u in users if u.get("id") == user_id), None)

        if not model_data or not user_data:
            if self.valves.show_status and __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": " Missing user or model data. Credit update skipped.",
                            "done": True,
                        },
                    }
                )
            return body

        fixed_price = float(model_data.get("fixed_price", 0))
        variable_price = float(model_data.get("variable_price", 0))
        credits = float(user_data.get("credits", 0))

        cost = prompt_tokens * fixed_price + completion_tokens * variable_price
        new_balance = max(0.0, credits - cost)

        try:
            async with httpx.AsyncClient() as client:
                update_res = await client.post(
                    f"{CREDITS_API_BASE_URL}/update",
                    json={
                        "id": user_id,
                        "credits": new_balance,
                        "actor": "auto-system",
                    },
                )
                update_res.raise_for_status()
        except Exception as e:
            if self.valves.show_status and __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f" Failed to deduct credits: {str(e)}",
                            "done": True,
                        },
                    }
                )
            return body

        if self.valves.show_status and __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": (
                            f"💳 Charged {cost:.3f} credits – New balance: {new_balance:.3f}"
                        ),
                        "done": True,
                    },
                }
            )

        return body
