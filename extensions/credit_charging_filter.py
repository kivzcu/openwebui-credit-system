"""
title: Credit management Charging credits
author: Miloslav Konopík, DDVVY
version: 1.0
"""

import os
from pydantic import BaseModel, Field
import httpx
import tiktoken
import re
from functools import partial

# Translation table for i18n support
TRANSLATIONS = {
    'cs-CZ': {
        'failed_to_load_metadata': 'Nepodařilo se načíst metadata kreditů: {}',
        'missing_user_model_data': 'Chybějící data uživatele nebo modelu. Stržení kreditů přeskočeno.',
        'free_model': '🆓 Bezplatný model - kredity neúčtovány.',
        'failed_to_deduct': 'Nepodařilo se stáhnout kredity: {}',
        'insufficient_credits': '⚠️ Nedostatek kreditů! Účtováno {actual_cost:.3f} z {full_cost:.3f} kreditů (chybí {shortage:.3f}) – Zůstatek: {new_balance:.3f}',
        'charged_credits': '💳 Účtováno {actual_cost:.3f} kreditů – Nový zůstatek: {new_balance:.3f}',
        'cost_estimate': '⚠️ Cena je odhad.'
    },
    'en': {  # Fallback language
        'failed_to_load_metadata': ' Failed to load credit metadata: {}',
        'missing_user_model_data': ' Missing user or model data. Credit update skipped.',
        'free_model': '🆓 Free model - no credits charged.',
        'failed_to_deduct': ' Failed to deduct credits: {}',
        'insufficient_credits': '⚠️ Insufficient credits! Charged {actual_cost:.3f} of {full_cost:.3f} credits (short by {shortage:.3f}) – Balance: {new_balance:.3f}',
        'charged_credits': '💳 Charged {actual_cost:.3f} credits – New balance: {new_balance:.3f}',
        'cost_estimate': '⚠️ The cost is an estimate.'
    }

}




class Filter:
    def _count_tokens_tiktoken(self, text: str, encoding_name: str) -> int:
        """Counts tokens using a specified tiktoken encoding."""
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))

    def _count_tokens_anthropic_dummy(self, text: str) -> int:
        """
        Example of a dummy counting function for a different library.
        e.g., from anthropic import Anthropic; client = Anthropic(); client.count_tokens(text)
        """
        # Dummy implementation: count words
        return len(text.split())

    class Valves(BaseModel):
        show_status: bool = Field(
            default=True, description="Zobrazit info o stržení kreditů"
        )
        credits_api_protocol: str = Field(default="https", description="API protocol (http or https)")
        credits_api_host: str = Field(default="147.228.121.27:8000", description="API host and port")
        ssl_verify: bool = Field(default=False, description="Verify SSL certificates")
        api_key: str = Field(default="vY97Yvh6qKywm8xE-ErTGfUofV0t1BiZ36wR3lLNHIY", description="API key for authentication")

    def __init__(self):
        self.valves = self.Valves()
        self.estimation_warning = ""
        # Map of model name patterns to their respective token counting functions.
        self.COUNT_FUNCTIONS = {
            r"^(gpt-4\.1|4o-mini|o4)": partial(
                self._count_tokens_tiktoken, encoding_name="o200k_base"
            ),
            r"^(claude-.*)": self._count_tokens_anthropic_dummy,
        }

    def _get_user_language(self, body):
        """Extract user language from body metadata"""
        try:
            return body.get('metadata', {}).get('variables', {}).get('{{USER_LANGUAGE}}', 'en')
        except:
            return 'en'

    def _translate(self, key, lang='en', **kwargs):
        """Get translated string for given key and language"""
        # Get the translation for the specific language, fallback to English
        translation = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, TRANSLATIONS['en'].get(key, key))
        
        # Ensure we have a valid translation string
        if translation is None:
            translation = key
        
        # Format the translation with any provided kwargs
        try:
            return translation.format(**kwargs)
        except:
            return translation

    def get_token_count(self, text: str, model_name: str) -> int:
        """
        Returns the token count for a given text and model.
        """
        # Check for a matching counting function for special cases
        for pattern, func in self.COUNT_FUNCTIONS.items():
            if re.match(pattern, model_name):
                return func(text)

        # If no special mapping, try getting encoding from model name
        try:
            encoding = tiktoken.encoding_for_model(model_name)
            return len(encoding.encode(text))
        except KeyError:
            self.estimation_warning = "⚠️ The cost is an estimate."
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))

    def count_tokens(self, msg: dict, model_name: str) -> int:
        content = msg.get("content", "")
        total_tokens = 0

        if isinstance(content, list):
            # Handle multi-modal content
            for item in content:
                if item.get("type") == "text":
                    text = item.get("text", "")
                    total_tokens += self.get_token_count(text, model_name)
        elif isinstance(content, str):
            # Handle text-only content
            total_tokens = self.get_token_count(content, model_name)
        else:
            # Handle unexpected content types
            total_tokens = 0

        return total_tokens

    async def outlet(
        self, body, __user__=None, __event_emitter__=None, __event_call__=None
    ):
        credits_api_base_url = f"{self.valves.credits_api_protocol}://{self.valves.credits_api_host}/api/credits"
        if not __user__:
            return body

        user_id = __user__.get("id")
        model_name = body.get("model", "gpt-3.5-turbo")
        self.estimation_warning = ""
        
        # Get user language for translations
        user_lang = self._get_user_language(body)

        messages = body.get("messages", [])
        if not messages:
            return body

        # print(body)

        # The last message is the completion, the rest are the prompt
        completion_message = messages[-1]

        usage = completion_message.get("usage")
        if usage and "prompt_tokens" in usage and "completion_tokens" in usage:
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
            self.estimation_warning = ""  # Exact cost, no warning
            actor = "model-usage"

            # Extract cached tokens and reasoning tokens (safe when details may be None)
            cached_tokens = (usage.get("prompt_tokens_details") or {}).get(
                "cached_tokens", 0
            )
            reasoning_tokens = (usage.get("completion_tokens_details") or {}).get(
                "reasoning_tokens", 0
            )

        else:
            # Fallback to manual counting if usage is not available
            prompt_messages = messages[:-1]
            prompt_tokens = sum(
                self.count_tokens(msg, model_name) for msg in prompt_messages
            )
            completion_tokens = self.count_tokens(completion_message, model_name)
            cached_tokens = 0  # Not available in manual counting
            reasoning_tokens = 0  # Not available in manual counting
            if self.estimation_warning:
                actor = "estimate-count"
            else:
                actor = "manual-count"

        try:
            # Set up headers with API key
            headers = {"X-API-Key": self.valves.api_key} if self.valves.api_key else {}

            async with httpx.AsyncClient(verify=self.valves.ssl_verify) as client:
                # Use optimized endpoints - get only the specific user and model we need
                user_res = await client.get(
                    f"{credits_api_base_url}/user/{user_id}", headers=headers
                )
                model_res = await client.get(
                    f"{credits_api_base_url}/model/{model_name}", headers=headers
                )
                user_res.raise_for_status()
                model_res.raise_for_status()
                user_data = user_res.json()
                model_data = model_res.json()
        except Exception as e:
            if self.valves.show_status and __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": self._translate('failed_to_load_metadata', user_lang).format(str(e)),
                            "done": True,
                        },
                    }
                )
            return body

        if not model_data or not user_data:
            if self.valves.show_status and __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": self._translate('missing_user_model_data', user_lang),
                            "done": True,
                        },
                    }
                )
            return body

        # Check if model is free
        is_free = model_data.get("is_free", False)

        if is_free:
            # For free models, skip credit deduction
            if self.valves.show_status and __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": self._translate('free_model', user_lang),
                            "done": True,
                        },
                    }
                )
            return body

        context_price = float(model_data.get("context_price", 0))
        generation_price = float(model_data.get("generation_price", 0))
        credits = float(user_data.get("credits", 0))

        cost = prompt_tokens * context_price + completion_tokens * generation_price

        try:
            # Set up headers with API key
            headers = {"X-API-Key": self.valves.api_key} if self.valves.api_key else {}

            async with httpx.AsyncClient(verify=self.valves.ssl_verify) as client:
                # Use the new optimized deduction endpoint
                deduction_res = await client.post(
                    f"{credits_api_base_url}/deduct-tokens",
                    json={
                        "user_id": user_id,
                        "model_id": model_name,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "cached_tokens": cached_tokens,
                        "reasoning_tokens": reasoning_tokens,
                        "actor": actor,
                    },
                    headers=headers,
                )
                deduction_res.raise_for_status()
                result = deduction_res.json()
                new_balance = result.get("new_balance", 0)
                actual_cost = result.get("deducted", 0)
                full_cost = result.get("cost", 0)
        except Exception as e:
            if self.valves.show_status and __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": self._translate('failed_to_deduct', user_lang).format(str(e)),
                            "done": True,
                        },
                    }
                )
            return body

        if self.valves.show_status and __event_emitter__:
            # Check if user had insufficient funds
            if actual_cost < full_cost:
                # Insufficient funds scenario
                shortage = full_cost - actual_cost
                description = self._translate('insufficient_credits', user_lang, 
                                            actual_cost=actual_cost, full_cost=full_cost, 
                                            shortage=shortage, new_balance=new_balance)
            else:
                # Normal scenario - full payment
                description = self._translate('charged_credits', user_lang, 
                                            actual_cost=actual_cost, new_balance=new_balance)

            if self.estimation_warning:
                estimate_warning = self._translate('cost_estimate', user_lang)
                description = estimate_warning + "<br/>" + description

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": description,
                        "done": True,
                    },
                }
            )

        return body
