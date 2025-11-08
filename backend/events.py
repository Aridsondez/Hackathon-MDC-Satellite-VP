from collections import deque

_EVENT_LOG = deque(maxlen=2000)

def emit_event(socketio, event_type, payload):
    rec = {"type": event_type, "payload": payload}
    _EVENT_LOG.append(rec)
    socketio.emit(event_type, payload)  # default namespace '/'

def dump_events(limit=200):
    # newest last
    start = max(0, len(_EVENT_LOG) - limit)
    return list(_EVENT_LOG)[start:]
