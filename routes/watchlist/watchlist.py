"""
routes/watchlist.py — CineLog (feature/watchlist branch)

Endpoints for the watchlist feature.
"""

from flask import Blueprint, jsonify, request
from services.watchlist_service import (
    add_to_watchlist, get_watchlist, AlreadyInWatchlistError,
    remove_from_watchlist, NotInWatchlistError,
)
from services.collection_service import FilmNotFoundError

watchlist_bp = Blueprint("watchlist", __name__)


@watchlist_bp.route("/<user_id>", methods=["GET"])
def view_watchlist(user_id):
    """GET /watchlist/<user_id> — Return the user's watchlist."""
    films = get_watchlist(user_id)
    return jsonify(films)


@watchlist_bp.route("/<user_id>/add", methods=["POST"])
def add_film(user_id):
    """
    POST /watchlist/<user_id>/add

    Body: { "film_id": "<uuid>", "public": false }
    """
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "JSON body must be an object"}), 400
    if "film_id" not in data:
        return jsonify({"error": "film_id is required"}), 400
    public = data.get("public", False)
    if not isinstance(public, bool):
        return jsonify({"error": "public must be a boolean"}), 400

    try:
        entry = add_to_watchlist(
            user_id=user_id, film_id=data["film_id"], public=public
        )
    except FilmNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except AlreadyInWatchlistError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify(entry.to_dict()), 201


@watchlist_bp.route("/<user_id>/remove", methods=["DELETE"])
def remove_film(user_id):
    """DELETE /watchlist/<user_id>/remove with a JSON film_id UUID."""
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "JSON body must be an object"}), 400
    if "film_id" not in data:
        return jsonify({"error": "film_id is required"}), 400

    try:
        remove_from_watchlist(user_id=user_id, film_id=data["film_id"])
    except NotInWatchlistError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"message": "Removed from watchlist"}), 200
