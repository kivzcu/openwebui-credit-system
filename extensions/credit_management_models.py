"""
title: Credit management Models
author: DDVVY
version: 1.0
"""

from pydantic import BaseModel, Field
import httpx


CREDITS_API_BASE_URL = "http://localhost:8000/api/credits"


class Action:
    class Valves(BaseModel):
        show_status: bool = Field(
            default=False, description="Not used – reserved for future options"
        )

    def __init__(self):
        self.valves = self.Valves()

    async def action(
        self, body, __user__=None, __event_emitter__=None, __event_call__=None
    ):
        model_name = body.get("model", "")

        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    f"{CREDITS_API_BASE_URL}/models"
                )
                res.raise_for_status()
                models = res.json()
        except Exception as e:
            body["messages"][-1][
                "content"
            ] += f"\n\n Failed to load model pricing: {str(e)}"
            return body

        model_data = next((m for m in models if m.get("id") == model_name), None)

        if not model_data:
            body["messages"][-1]["content"] += "\n\n Model not found in pricing list."
            return body

        fixed = model_data.get("fixed_price", 0)
        variable = model_data.get("variable_price", 0)

        body["messages"][-1]["content"] += (
            f"\n\n📊 Model **{model_name}** pricing:\n"
            f"• Prompt (input): {fixed} credits/token\n"
            f"• Completion (output): {variable} credits/token"
        )

        return body
