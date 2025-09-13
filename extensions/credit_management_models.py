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
        'completion_price': '• Dokončení (výstup): {} kreditů/token'
    },
    'en': {  # Fallback language
        'failed_to_load_pricing': ' Failed to load model pricing: {}',
        'model_not_found_pricing': ' Model not found in pricing list.',
        'model_pricing_title': '📊 Model **{}** pricing:',
        'free_model_pricing': '🆓 **FREE MODEL** - No credits required',
        'prompt_price': '• Prompt (input): {} credits/token',
        'completion_price': '• Completion (output): {} credits/token'
    }
}

# Support both HTTP and HTTPS based on environment
CREDITS_API_PROTOCOL = os.getenv("CREDITS_API_PROTOCOL", "http")
CREDITS_API_HOST = os.getenv("CREDITS_API_HOST", "localhost:8000")
CREDITS_API_BASE_URL = f"{CREDITS_API_PROTOCOL}://{CREDITS_API_HOST}/api/credits"

# SSL verification settings
SSL_VERIFY = os.getenv("CREDITS_API_SSL_VERIFY", "false").lower() == "true"

# API Key for authentication
API_KEY = os.getenv("CREDITS_API_KEY")
if not API_KEY:
    print("WARNING: CREDITS_API_KEY not set. Model pricing lookup may not function properly.")


class Action:
    class Valves(BaseModel):
        show_status: bool = Field(
            default=False, description="Not used – reserved for future options"
        )

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

    async def action(
        self, body, __user__=None, __event_emitter__=None, __event_call__=None
    ):
        model_name = body.get("model", "")
        
        # Get user language for translations
        user_lang = self._get_user_language(body)

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
            body["messages"][-1]["content"] += (
                f"\n\n{self._translate('model_pricing_title', user_lang).format(model_name)}\n"
                f"{self._translate('prompt_price', user_lang).format(context_price)}\n"
                f"{self._translate('completion_price', user_lang).format(generation_price)}"
            )

        return body
