"""
title: Credit management  enough credits
author: DDVVY
version: 1.0
"""

import os
from pydantic import BaseModel, Field
import httpx

# Support both HTTP and HTTPS based on environment
CREDITS_API_PROTOCOL = os.getenv("CREDITS_API_PROTOCOL", "https")  # Default to HTTPS
CREDITS_API_HOST = os.getenv("CREDITS_API_HOST", "147.228.121.27:8000")
CREDITS_API_BASE_URL = f"{CREDITS_API_PROTOCOL}://{CREDITS_API_HOST}/api/credits"

# SSL verification settings
SSL_VERIFY = os.getenv("CREDITS_API_SSL_VERIFY", "false").lower() == "true"

# API Key for authentication
API_KEY = os.getenv("CREDITS_API_KEY", "vY97Yvh6qKywm8xE-ErTGfUofV0t1BiZ36wR3lLNHIY")


# If not available in your project, define your own exception:
class FilterException(Exception):
    pass


class Filter:
    """
    Filters prompts based on user's available credits. Blocks prompt execution if
    the estimated cost exceeds available user credits. Fetches cost and user data
    from a backend API.
    """

    class Valves(BaseModel):
        show_status: bool = Field(
            default=True, description="Show credit status message to the user."
        )

    def __init__(self):
        self.valves = self.Valves()

    def format_credit_amount(self, amount):
        """Format credit amount to avoid scientific notation and excessive precision"""
        if amount == 0:
            return "0"
        
        # Convert to decimal string to avoid scientific notation
        decimal_str = f"{amount:.10f}"
        
        # Remove trailing zeros and decimal point if not needed
        if '.' in decimal_str:
            decimal_str = decimal_str.rstrip('0').rstrip('.')
        
        # If the result is empty (very small number), show minimum precision
        if not decimal_str or decimal_str == '0.':
            return f"{amount:.8f}".rstrip('0').rstrip('.')
        
        return decimal_str

    async def inlet(
        self, body, __user__=None, __event_emitter__=None, __event_call__=None
    ):
        user_id = __user__.get("id")
        model_name = body.get("model")
        prompt_text = body["messages"][-1]["content"]
        prompt_tokens = body.get("prompt_tokens") or max(len(prompt_text) // 4, 1)

        try:
            # Set up headers with API key
            headers = {"X-API-Key": API_KEY} if API_KEY else {}
            
            async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
                # Use optimized endpoints - get only specific user and model
                user_res = await client.get(
                    f"{CREDITS_API_BASE_URL}/user/{user_id}",
                    headers=headers
                )
                model_res = await client.get(
                    f"{CREDITS_API_BASE_URL}/model/{model_name}",
                    headers=headers
                )
                user_res.raise_for_status()
                model_res.raise_for_status()
                user_data = user_res.json()
                model_data = model_res.json()
        except Exception as e:
            body["messages"][-1][
                "content"
            ] += f"\n\nUnable to load credit data: {str(e)}"
            return body

        user_data = user_data
        if not user_data:
            body["messages"][-1]["content"] += "\n\nUser data not found."
            return body

        model_data = model_data
        if not model_data:
            body["messages"][-1]["content"] += "\n\nModel not found in cost list."
            return body

        # Check if model is free - if so, allow the request without credit check
        is_free = model_data.get("is_free", False)
        if is_free:
            if self.valves.show_status and __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "🆓 Free model - no credits charged.",
                            "done": True,
                        },
                    }
                )
            return body

        context_price = model_data.get("context_price", 0)
        cost = prompt_tokens * context_price
        credits = user_data.get("credits", 0)

        if credits < cost:
            if self.valves.show_status and __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Insufficient credits – prompt blocked.",
                            "done": True,
                        },
                    }
                )

            raise FilterException(
                f"You do not have enough credits: {self.format_credit_amount(credits)} available, minimum {self.format_credit_amount(cost)} required."
            )

        # Prompt is allowed, but no success message is emitted
        return body
