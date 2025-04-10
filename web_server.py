from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import json
import time

from game_utils import WEB_SERVER_PORT

# Create Flask app and SocketIO instance
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Route for the main page
@app.route('/')
def index():
    return render_template('index.html')

# Start the WebSocket server
def start_server():
    socketio.run(app, host='0.0.0.0', port=WEB_SERVER_PORT, debug=False, allow_unsafe_werkzeug=True)

# Function to emit data to clients
def emit_device_data(device_name, data):
    socketio.emit('device_update', {'device': device_name, 'data': data})