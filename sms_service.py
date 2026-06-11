
from pathlib import Path

import logging
import africastalking
from config import AT_USERNAME, AT_API_KEY

logger = logging.getLogger(__name__)

# Initialise AT once when module loads
africastalking.initialize(
    username=AT_USERNAME,
    api_key=AT_API_KEY
)

sms = africastalking.SMS

def send_sms(to: str, message: str) -> bool:
    """
    Send an SMS via Africa's Talking.
    Returns True if successful, False if failed.
    """
    try:
        response = sms.send(
            message=message,
            recipients=[to]
        )
        logger.info(f"SMS sent to {to}: {response}")
        return True

    except Exception as e:
        logger.error(f"Failed to send SMS to {to}: {e}")
        return False