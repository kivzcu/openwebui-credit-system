"""
title: Credit management Models
author: DDVVY
version: 1.0
"""

import os
from pydantic import BaseModel, Field
import httpx


# Support both HTTP and HTTPS based on environment
CREDITS_API_PROTOCOL = os.getenv("CREDITS_API_PROTOCOL", default="https")  # Default to HTTPS
CREDITS_API_HOST = os.getenv("CREDITS_API_HOST", "147.228.121.27:8000")
CREDITS_API_BASE_URL = f"{CREDITS_API_PROTOCOL}://{CREDITS_API_HOST}/api/credits"

# SSL verification settings
SSL_VERIFY = os.getenv("CREDITS_API_SSL_VERIFY", "false").lower() == "true"

# API Key for authentication
API_KEY = os.getenv("CREDITS_API_KEY", "vY97Yvh6qKywm8xE-ErTGfUofV0t1BiZ36wR3lLNHIY")


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
            # Set up headers with API key
            headers = {"X-API-Key": API_KEY} if API_KEY else {}
            
            async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
                # Use optimized endpoint for specific model
                res = await client.get(
                    f"{CREDITS_API_BASE_URL}/model/{model_name}",
                    headers=headers
                )
                res.raise_for_status()
                model_data = res.json()
        except Exception as e:
            body["messages"][-1][
                "content"
            ] += f"\n\n Failed to load model pricing: {str(e)}"
            return body

        if not model_data:
            body["messages"][-1]["content"] += "\n\n Model not found in pricing list."
            return body

        context_price = model_data.get("context_price", 0)
        generation_price = model_data.get("generation_price", 0)

        body["messages"][-1]["content"] += (
            f"\n\n📊 Model **{model_name}** pricing:\n"
            f"• Prompt (input): {context_price} credits/token\n"
            f"• Completion (output): {generation_price} credits/token"
        )

        return body
