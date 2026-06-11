

import logging
logger = logging.getLogger(__name__)

from llm_client import anthropic_client, MODEL
client = anthropic_client

# Intent categories and what triggers them
from prompts_v2 import INTENT_CLASSIFIER_PROMPT
INTENT_PROMPT = INTENT_CLASSIFIER_PROMPT

def classify_intent(message: str) -> str:
    """
    Classify a patient message as 'faq', 'booking', or 'general'.

    Returns:
        'faq', 'booking', or 'general'
    """
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=10,
            system=INTENT_PROMPT,
            messages=[{"role": "user", "content": message}]
        )
        intent = response.content[0].text.strip().lower()

        if intent not in ("faq", "booking", "general"):
            logger.warning(f"Unexpected intent '{intent}' — defaulting to faq")
            intent = "faq"

        logger.info(f"Intent: '{intent}' | message: '{message}'")
        return intent

    except Exception as e:
        logger.error(f"Intent classification failed: {e} — defaulting to faq")
        return "faq"