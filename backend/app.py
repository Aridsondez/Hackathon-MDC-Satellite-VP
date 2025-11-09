from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from routes.control import bp as control_bp
from routes.smoke import bp as smoke_bp
from routes.tasks import bp as tasks_bp
from routes.state import bp as state_bp
from routes.economics import bp as economics_bp
from routes.solana import bp as solana_bp
from core import scheduler
from seeds.seed_state import seed_state
from core import state as core_state
from config import CONFIG as GLOBAL_CONFIG


# Use threading mode to avoid eventlet/gevent on Python 3.13
socketio = SocketIO(async_mode='threading', cors_allowed_origins="*")

def create_app():
    app = Flask(__name__)
    app.register_blueprint(control_bp, url_prefix="/api")
    app.register_blueprint(smoke_bp,   url_prefix="/api")
    app.register_blueprint(tasks_bp,   url_prefix="/api")
    app.register_blueprint(state_bp,   url_prefix="/api")
    app.register_blueprint(economics_bp, url_prefix="/api")
    app.register_blueprint(solana_bp, url_prefix="/api")
    socketio.init_app(app)
    seed_state()
    socketio.init_app(app)
    core_state.init_globals(GLOBAL_CONFIG, socketio)
    seed_state()
    scheduler.start(socketio)
    return app

app = create_app()
CORS(app) 

if __name__ == "__main__":
    # Werkzeug dev server + simple-websocket will handle WS in threading mode
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)
