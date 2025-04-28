import os
from flask import Blueprint, request, jsonify, make_response
from http import HTTPStatus
import firebase_admin
from firebase_admin import firestore
import logging
from jsonschema import ValidationError
from api.db import db
from api.models import ActiveProjectRequest, ProjectRequest, UserRequest
from api.utils import create_default_kanban

logger = logging.getLogger(__name__)
firebase_bp = Blueprint("firebase", __name__, url_prefix="/api/firebase")


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


@firebase_bp.route("/users/<uid>", methods=["GET"])
def get_user(uid: str | None):
    try:
        if not uid:
            return jsonify({"error": "User ID is required"}), HTTPStatus.BAD_REQUEST

        user_ref = db.collection("users").document(uid)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({"error": "User not found"}), HTTPStatus.NOT_FOUND

        resp = jsonify(user_doc.to_dict())
        resp.headers["Access-Control-Allow-Origin"] = os.getenv(
            "FRONTEND_URL", "http://localhost:3000"
        )
        return resp, HTTPStatus.OK

    except firebase_admin.exceptions.FirebaseError as e:
        logger.error(f"Firebase error: {str(e)}")
        return (
            jsonify({"error": "Firebase service error", "code": "FIREBASE_ERROR"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}")
        return (
            jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )


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

        user_ref = db.collection("users").document(uid)
        user_doc = user_ref.get()
        server_status = None

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
            server_status = HTTPStatus.CREATED
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
            server_status = HTTPStatus.OK
        # Get updated user data
        updated_user = user_ref.get().to_dict()
        resp = jsonify(updated_user)
        resp.headers["Access-Control-Allow-Origin"] = os.getenv(
            "FRONTEND_URL", "http://localhost:3000"
        )

        return resp, server_status

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


@firebase_bp.route("/users/active-project", methods=["POST"])
def update_active_project():
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

        data = ActiveProjectRequest(**request.json)
        user_id = data.userId
        project_id = data.projectId

        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            logger.warning(f"User not found: {user_id}")
            return (
                jsonify({"error": "User not found", "code": "NOT_FOUND"}),
                HTTPStatus.NOT_FOUND,
            )

        update_data = {
            "activeProjectId": project_id,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
        user_ref.update(update_data)

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
        logger.error(f"Unexpected error: {str(e)}")
        return (
            jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@firebase_bp.route("/projects", methods=["POST"])
def create_project():
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

        data = ProjectRequest(**request.json)
        user_id = data.userId
        title = data.title
        description = data.description
        status = data.status
        kanban = data.kanban or create_default_kanban()

        project_ref = db.collection("projects").document()
        project_data = {
            "id": project_ref.id,
            "userId": user_id,
            "title": title,
            "description": description,
            "status": status,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "kanban": kanban.model_dump(),
        }

        project_ref.set(project_data)
        created_project = project_ref.get()

        if not created_project.exists:
            logger.error("Failed to create project")
            return (
                jsonify(
                    {"error": "Failed to create project", "code": "CREATION_FAILED"}
                ),
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

        resp = jsonify(created_project.to_dict())
        resp.headers["Access-Control-Allow-Origin"] = os.getenv(
            "FRONTEND_URL", "http://localhost:3000"
        )

        return resp, HTTPStatus.CREATED

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
        logger.error(f"Unexpected error: {str(e)}")
        return (
            jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@firebase_bp.route("/projects/<uid>", methods=["GET"])
def get_projects(uid: str | None):
    try:
        if not uid:
            return jsonify({"error": "User ID is required"}), HTTPStatus.BAD_REQUEST

        projects_ref = db.collection("projects")
        projects_query = projects_ref.where("userId", "==", uid).order_by(
            "updatedAt", "DESCENDING"
        )
        projects_docs = list(projects_query.get())

        if not projects_docs:
            return (
                jsonify({"error": "No projects were found for this user"}),
                HTTPStatus.NOT_FOUND,
            )

        projects = [project.to_dict() for project in projects_docs]
        resp = jsonify(projects)
        resp.headers["Access-Control-Allow-Origin"] = os.getenv(
            "FRONTEND_URL", "http://localhost:3000"
        )

        return resp, HTTPStatus.OK

    except firebase_admin.exceptions.FirebaseError as e:
        logger.error(f"Firebase error: {str(e)}")
        return (
            jsonify({"error": "Firebase service error", "code": "FIREBASE_ERROR"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return (
            jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
