import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from http import HTTPStatus
from api.ai import ai_bp
import firebase_admin
from firebase_admin import credentials
import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [os.getenv("FRONTEND_URL", "http://localhost:3000")],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Accept", "Authorization"],
            "expose_headers": ["Content-Type"],
            "max_age": 86400,
        }
    },
)

# Initialize Firebase
try:
    cred = credentials.Certificate(os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH"))
    firebase_admin.initialize_app(cred)
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {str(e)}")
    raise

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.error("OpenAI API key not found")
    raise ValueError("OpenAI API key not found")


# Global error handlers
@app.errorhandler(404)
def not_found(e):
    logger.warning(f"Not found: {request.path}")
    return (
        jsonify({"error": "Resource not found", "code": "NOT_FOUND"}),
        HTTPStatus.NOT_FOUND,
    )


@app.errorhandler(405)
def method_not_allowed(e):
    logger.warning(f"Method not allowed: {request.method} {request.path}")
    return (
        jsonify({"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}),
        HTTPStatus.METHOD_NOT_ALLOWED,
    )


# Register blueprints
app.register_blueprint(ai_bp)


@app.route("/")
def health_check():
    return jsonify({"status": "API is running"}), HTTPStatus.OK


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3001))
    logger.info(f"Starting Flask on port {port}")
    try:
        app.run(debug=True, host="0.0.0.0", port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise
