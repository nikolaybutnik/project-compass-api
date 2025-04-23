import os
from flask import Blueprint, request, jsonify, make_response
from http import HTTPStatus
import firebase_admin
from firebase_admin import firestore
import logging

from jsonschema import ValidationError
from openai import BaseModel
from api.db import db

logger = logging.getLogger(__name__)
firebase_bp = Blueprint("firebase", __name__, url_prefix="/api/firebase")


class UserRequest(BaseModel):
    uid: str
    email: str | None = None
    displayName: str | None = None
    photoURL: str | None = None


@firebase_bp.before_request
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


@firebase_bp.after_request
def log_response(response):
    logger.info(f"Response headers: {response.headers}")
    return response


@firebase_bp.route("/users", methods=["POST"])
def create_or_update_user():
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

        data = UserRequest(**request.json)
        uid = data.uid

        if not uid:
            return jsonify({"error": "User ID is required"}), HTTPStatus.BAD_REQUEST

        # Get or create user document
        user_ref = db.collection("users").document(uid)
        user_doc = user_ref.get()

        if not user_doc.exists:
            # Create new user
            user_data = {
                "id": uid,
                "email": data.email,
                "displayName": data.displayName or data.email.split("@")[0],
                "photoURL": data.photoURL,
                "role": "user",
                "activeProjectId": None,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "lastLogin": firestore.SERVER_TIMESTAMP,
            }
            user_ref.set(user_data)
        else:
            # Update existing user
            update_data = {
                "lastLogin": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }

            if data.email:
                update_data["email"] = data.email
            if data.displayName:
                update_data["displayName"] = data.displayName
            if data.photoURL:
                update_data["photoURL"] = data.photoURL

            user_ref.update(update_data)

        # Get updated user data
        updated_user = user_ref.get().to_dict()
        resp = jsonify(updated_user)
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
    except firebase_admin.exceptions.FirebaseError as e:
        logger.error(f"Firebase error: {str(e)}")
        return (
            jsonify({"error": "Firebase service error", "code": "FIREBASE_ERROR"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Error creating/updating user: {str(e)}")
        return (
            jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
