import os
import firebase_admin
from firebase_admin import firestore, credentials
import logging

logger = logging.getLogger(__name__)

try:
    cred = credentials.Certificate(os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH"))
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except ValueError as e:
    if "already exists" in str(e):
        db = firestore.client()  # Use existing app
    else:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        raise
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {str(e)}")
    raise
