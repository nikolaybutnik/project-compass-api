import os
from flask import Blueprint, request, jsonify, make_response
from http import HTTPStatus
from pydantic import ValidationError
import logging
import openai
from api.models import ChatRequest

logger = logging.getLogger(__name__)
ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@ai_bp.before_request
def log_request():
    logger.info(
        f"Request: {request.method} {request.path} Headers: {request.headers.get('User-Agent')}"
    )
    if request.method == "OPTIONS":
        response = make_response()
        response.headers["Access-Control-Allow-Origin"] = os.getenv(
            "FRONTEND_URL", "http://localhost:3000"
        )
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Accept, Authorization"
        )
        response.headers["Access-Control-Max-Age"] = "86400"
        return response, HTTPStatus.OK


@ai_bp.after_request
def log_response(response):
    logger.info(f"Response headers: {response.headers}")
    return response


@ai_bp.route("/chat", methods=["POST"])
def ai_chat():
    try:
        if not request.is_json:
            logger.warning("Invalid content type: expected application/json")
            return (
                jsonify(
                    {
                        "error": "Content-Type must be application/json",
                        "code": "INVALID_CONTENT_TYPE",
                    }
                ),
                HTTPStatus.BAD_REQUEST,
            )

        data = ChatRequest(**request.json)
        logger.info(f"Chat request: model={data.model}, messages={len(data.messages)}")

        response = openai.chat.completions.create(
            model=data.model,
            messages=data.messages,
            tools=data.tools,
            tool_choice=data.tool_choice,
        )

        resp = jsonify(response.model_dump())
        resp.headers["Access-Control-Allow-Origin"] = os.getenv(
            "FRONTEND_URL", "http://localhost:3000"
        )
        return resp, HTTPStatus.OK

    except ValidationError as e:
        logger.warning(f"Invalid request: {str(e)}")
        return (
            jsonify(
                {
                    "error": "Invalid request data",
                    "details": e.errors(),
                    "code": "VALIDATION_ERROR",
                }
            ),
            HTTPStatus.BAD_REQUEST,
        )
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return (
            jsonify({"error": "Failed to process AI request", "code": "OPENAI_ERROR"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return (
            jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
