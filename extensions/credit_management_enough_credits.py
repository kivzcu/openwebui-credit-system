"""
title: Credit management  enough credits
author: DDVVY
version: 1.0
"""

import os
from pydantic import BaseModel, Field
import httpx

# Translation table for i18n support
TRANSLATIONS = {
    'cs-CZ': {
        'failed_to_load_data': 'Nepodařilo se načíst data kreditů: {}',
        'user_not_found': 'Data uživatele nenalezena.',
        'model_not_found': 'Model nenalezen v ceníku.',
        'free_model': '🆓 Bezplatný model - kredity neúčtovány.',
        'insufficient_prompt_blocked': 'Nedostatek kreditů – prompt zablokován.',
        'insufficient_credits_error': 'Nemáte dostatek kreditů: {} k dispozici, minimálně {} potřeba.'
    },
    'en': {  # Fallback language
        'failed_to_load_data': 'Unable to load credit data: {}',
        'user_not_found': 'User data not found.',
        'model_not_found': 'Model not found in cost list.',
        'free_model': '🆓 Free model - no credits charged.',
        'insufficient_prompt_blocked': 'Insufficient credits – prompt blocked.',
        'insufficient_credits_error': 'You do not have enough credits: {} available, minimum {} required.'
    }
}




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
        credits_api_protocol: str = Field(default="http", description="API protocol (http or https)")
        credits_api_host: str = Field(default="localhost:8000", description="API host and port")
        ssl_verify: bool = Field(default=False, description="Verify SSL certificates")
        api_key: str = Field(default="", description="API key for authentication")

    def __init__(self):
        self.valves = self.Valves()

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
        credits_api_base_url = f"{self.valves.credits_api_protocol}://{self.valves.credits_api_host}/api/credits"
        user_id = __user__.get("id")
        model_name = body.get("model")
        prompt_text = body["messages"][-1]["content"]
        prompt_tokens = body.get("prompt_tokens") or max(len(prompt_text) // 4, 1)
        
        # Get user language for translations
        user_lang = self._get_user_language(body)

        try:
            # Set up headers with API key
            headers = {"X-API-Key": self.valves.api_key} if self.valves.api_key else {}
            
            async with httpx.AsyncClient(verify=self.valves.ssl_verify) as client:
                # Use optimized endpoints - get only specific user and model
                user_res = await client.get(
                    f"{credits_api_base_url}/user/{user_id}",
                    headers=headers
                )
                model_res = await client.get(
                    f"{credits_api_base_url}/model/{model_name}",
                    headers=headers
                )
                user_res.raise_for_status()
                model_res.raise_for_status()
                user_data = user_res.json()
                model_data = model_res.json()
        except Exception as e:
            body["messages"][-1][
                "content"
            ] += f"\n\n{self._translate('failed_to_load_data', user_lang).format(str(e))}"
            return body

        user_data = user_data
        if not user_data:
            body["messages"][-1]["content"] += f"\n\n{self._translate('user_not_found', user_lang)}"
            return body

        model_data = model_data
        if not model_data:
            body["messages"][-1]["content"] += f"\n\n{self._translate('model_not_found', user_lang)}"
            return body

        # Check if model is free - if so, allow the request without credit check
        is_free = model_data.get("is_free", False)
        if is_free:
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

        context_price = model_data.get("context_price", 0)
        cost = prompt_tokens * context_price
        credits = user_data.get("credits", 0)

        if credits < cost:
            if self.valves.show_status and __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": self._translate('insufficient_prompt_blocked', user_lang),
                            "done": True,
                        },
                    }
                )

            raise FilterException(
                self._translate('insufficient_credits_error', user_lang).format(
                    self.format_credit_amount(credits), 
                    self.format_credit_amount(cost)
                )
            )

        # Prompt is allowed, but no success message is emitted
        return body
