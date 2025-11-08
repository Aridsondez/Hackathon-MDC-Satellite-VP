from flask import Blueprint, jsonify
from core.state import snapshot

bp = Blueprint("state", __name__)

@bp.get("/state")
def get_state():
    return jsonify(snapshot())
