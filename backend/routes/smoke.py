from flask import Blueprint, request, jsonify
from core.smoke_consumer import start_smoke, stop_smoke

bp = Blueprint("smoke", __name__)

@bp.post("/smoke/start")
def start():
    cfg = request.get_json(force=True)
    start_smoke(qps=cfg.get("qps", 30), burst=cfg.get("burst", 10))
    return jsonify({"ok": True})

@bp.post("/smoke/stop")
def stop():
    stop_smoke()
    return jsonify({"ok": True})
