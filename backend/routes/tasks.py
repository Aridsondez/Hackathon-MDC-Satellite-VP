from flask import Blueprint, request, jsonify
from core.models import Task
from core import state
from core.state import snapshot

bp = Blueprint("tasks", __name__)

@bp.post("/tasks")
def create_task():
    data = request.get_json(force=True)
    t = Task(**data)
    with state.LOCK:
        state.TASK_QUEUE.append(t)
    return jsonify(t.model_dump())

@bp.get("/state")
def get_state():
    return jsonify(snapshot())