import threading
import time

import serial
from flask import Flask, jsonify, render_template_string, request

# Change this to your ESP32's serial port
SERIAL_PORT = "/dev/cu.usbserial-0001"
BAUD_RATE = 115200

app = Flask(__name__)

# Open the USB serial connection
esp = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
time.sleep(2)  # ESP32 may reset when serial opens

serial_lock = threading.Lock()

HTML = """
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ESP32 LED Controller</title>
  <style>
    body {
      font-family: system-ui, sans-serif;
      max-width: 420px;
      margin: 50px auto;
      padding: 20px;
      background: #f4f4f5;
      color: #18181b;
    }
    section {
      background: white;
      padding: 20px;
      margin: 16px 0;
      border-radius: 14px;
    }
    button {
      padding: 12px 24px;
      margin: 6px 5px 0 0;
      border: 0;
      border-radius: 8px;
      cursor: pointer;
      font-size: 16px;
    }
    .on { background: #16a34a; color: white; }
    .off { background: #e4e4e7; color: #18181b; }
    #status { color: #52525b; }
  </style>
</head>
<body>
  <h1>ESP32 Controller</h1>
  <p>Control LEDs through USB serial.</p>

  <section>
    <h2>LED 1 · GPIO 25</h2>
    <button class="on" onclick="control(1, 'on')">ON</button>
    <button class="off" onclick="control(1, 'off')">OFF</button>
  </section>

  <section>
    <h2>LED 2 · GPIO 32</h2>
    <button class="on" onclick="control(2, 'on')">ON</button>
    <button class="off" onclick="control(2, 'off')">OFF</button>
  </section>

  <p id="status">Ready</p>

  <script>
    async function control(led, state) {
      const status = document.getElementById('status');
      status.textContent = 'Sending command...';

      try {
        const response = await fetch(`/api/led/${led}`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({state})
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error);

        status.textContent = `LED ${led} turned ${state.toUpperCase()}`;
      } catch (error) {
        status.textContent = 'Error: ' + error.message;
      }
    }
  </script>
</body>
</html>
"""


def send_command(command):
    with serial_lock:
        esp.reset_input_buffer()
        esp.write((command + "\n").encode())
        esp.flush()
        return esp.readline().decode(errors="replace").strip()


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/led/<int:led>", methods=["POST"])
def set_led(led):
    if led not in (1, 2):
        return jsonify(error="LED must be 1 or 2"), 400

    data = request.get_json(silent=True) or {}
    state = data.get("state")

    if state not in ("on", "off"):
        return jsonify(error="state must be on or off"), 400

    command = f"LED{led}_{state.upper()}"
    reply = send_command(command)

    if not reply.startswith("OK"):
        return jsonify(error="No valid response from ESP32", response=reply), 504

    return jsonify(led=led, state=state, response=reply)


@app.route("/api/status")
def status():
    reply = send_command("STATUS")
    return jsonify(response=reply)


if __name__ == "__main__":
    print("Open http://127.0.0.1:5470")
    app.run(host="0.0.0.0", port=5470, debug=False)
