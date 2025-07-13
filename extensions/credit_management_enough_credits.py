"""
title: Credit management  enough credits
author: DDVVY
version: 1.0
"""

from pydantic import BaseModel, Field
import httpx

CREDITS_API_BASE_URL = "http://localhost:8000/api/credits"


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

    async def inlet(
        self, body, __user__=None, __event_emitter__=None, __event_call__=None
    ):
        user_id = __user__.get("id")
        model_name = body.get("model")
        prompt_text = body["messages"][-1]["content"]
        prompt_tokens = body.get("prompt_tokens") or max(len(prompt_text) // 4, 1)

        try:
            async with httpx.AsyncClient() as client:
                # Use optimized endpoints - get only specific user and model
                user_res = await client.get(
                    f"{CREDITS_API_BASE_URL}/user/{user_id}"
                )
                model_res = await client.get(
                    f"{CREDITS_API_BASE_URL}/model/{model_name}"
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
                f"You do not have enough credits: {credits} available, minimum {cost:.2f} required."
            )

        # Prompt is allowed, but no success message is emitted
        return body
