"""
title: Credit management Models
author: DDVVY
version: 1.0
"""

import os
from pydantic import BaseModel, Field
import httpx

# Translation table for i18n support
TRANSLATIONS = {
    'cs-CZ': {
        'failed_to_load_pricing': 'Nepodařilo se načíst ceník modelu: {}',
        'model_not_found_pricing': 'Model nenalezen v ceníku.',
        'model_pricing_title': '📊 Ceník modelu **{}**:',
        'free_model_pricing': '🆓 **BEZPLATNÝ MODEL** - Žádné kredity nejsou vyžadovány',
        'prompt_price': '• Prompt (vstup): {} kreditů/token',
        'completion_price': '• Dokončení (výstup): {} kreditů/token',
        'prompt_price_1m': '• Prompt (vstup, 1M tokenů): {} kreditů',
        'completion_price_1m': '• Dokončení (výstup, 1M tokenů): {} kreditů'
    },
    'en': {  # Fallback language
        'failed_to_load_pricing': ' Failed to load model pricing: {}',
        'model_not_found_pricing': ' Model not found in pricing list.',
        'model_pricing_title': '📊 Model **{}** pricing:',
        'free_model_pricing': '🆓 **FREE MODEL** - No credits required',
        'prompt_price': '• Prompt (input): {} credits/token',
        'completion_price': '• Completion (output): {} credits/token',
        'prompt_price_1m': '• Prompt (input, 1M tokens): {} credits',
        'completion_price_1m': '• Completion (output, 1M tokens): {} credits'
    }
}




class Action:
    class Valves(BaseModel):
        show_status: bool = Field(
            default=False, description="Not used – reserved for future options"
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

    def _format_credits(self, value):
        """Format credit values with commas and trim unnecessary decimals."""
        try:
            s = f"{value:,.6f}"
            s = s.rstrip('0').rstrip('.')
            return s
        except:
            return str(value)

    async def action(
        self, body, __user__=None, __event_emitter__=None, __event_call__=None
    ):
        credits_api_base_url = f"{self.valves.credits_api_protocol}://{self.valves.credits_api_host}/api/credits"
        model_name = body.get("model", "")
        
        # Get user language for translations
        user_lang = self._get_user_language(body)

        try:
            # Set up headers with API key
            headers = {"X-API-Key": self.valves.api_key} if self.valves.api_key else {}
            
            async with httpx.AsyncClient(verify=self.valves.ssl_verify) as client:
                # Use optimized endpoint for specific model
                res = await client.get(
                    f"{credits_api_base_url}/model/{model_name}",
                    headers=headers
                )
                res.raise_for_status()
                model_data = res.json()
        except Exception as e:
            body["messages"][-1][
                "content"
            ] += f"\n\n{self._translate('failed_to_load_pricing', user_lang).format(str(e))}"
            return body

        if not model_data:
            body["messages"][-1]["content"] += f"\n\n{self._translate('model_not_found_pricing', user_lang)}"
            return body

        context_price = model_data.get("context_price", 0)
        generation_price = model_data.get("generation_price", 0)
        is_free = model_data.get("is_free", False)

        if is_free:
            body["messages"][-1]["content"] += (
                f"\n\n{self._translate('model_pricing_title', user_lang).format(model_name)}\n"
                f"{self._translate('free_model_pricing', user_lang)}"
            )
        else:
            # Multiply per-token prices by 1,000,000 and format
            context_price_1m = context_price * 1_000_000
            generation_price_1m = generation_price * 1_000_000

            body["messages"][-1]["content"] += (
                f"\n\n{self._translate('model_pricing_title', user_lang).format(model_name)}\n"
                f"{self._translate('prompt_price_1m', user_lang).format(self._format_credits(context_price_1m))}\n"
                f"{self._translate('completion_price_1m', user_lang).format(self._format_credits(generation_price_1m))}"
            )

        return body
