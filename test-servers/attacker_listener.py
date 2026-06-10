"""
Attacker-controlled listener server.
Runs on port 9999 and logs all incoming requests (GET/POST).
Captures exfiltrated data from successful prompt injection attacks.

Usage:
    python test-servers/attacker_listener.py
"""
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('attacker-listener')

captured = []


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'method': request.method,
        'path': f'/{path}',
        'query': dict(request.args),
        'headers': dict(request.headers),
        'body': request.get_data(as_text=True),
    }
    captured.append(entry)
    log.info(f"=== EXFILTRATION DETECTED ===")
    log.info(f"Method: {request.method}, Path: /{path}")
    if request.args:
        log.info(f"Query: {dict(request.args)}")
    if request.get_data(as_text=True):
        log.info(f"Body: {request.get_data(as_text=True)[:500]}")
    log.info(f"==============================")
    return jsonify({'status': 'received'})


@app.route('/_captured', methods=['GET'])
def view_captured():
    """View all captured exfiltration attempts."""
    return jsonify(captured)


@app.route('/_clear', methods=['POST'])
def clear_captured():
    captured.clear()
    return jsonify({'status': 'cleared'})


if __name__ == '__main__':
    log.info("=" * 50)
    log.info("ATTACKER LISTENER on port 9999")
    log.info("Captures all exfiltration attempts from workflows")
    log.info("View captured data: http://localhost:9999/_captured")
    log.info("=" * 50)
    app.run(host='0.0.0.0', port=9999, debug=False)
