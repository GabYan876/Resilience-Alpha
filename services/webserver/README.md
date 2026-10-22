# ESP32 LED Controller

A lightweight Python Flask web server that controls two LEDs connected to an ESP32 over USB serial. Provides a web interface and a REST API accessible from your local network.

## Features

- Control two LEDs independently.
- Web interface with ON/OFF buttons.
- REST API for LED control and status.
- USB serial communication between Python and ESP32.
- Access from other devices on the same local network.

## Architecture

```text
Phone / Browser / API Client
           |
           | HTTP
           v
    Python Flask Server
       Port 5000
           |
           | USB Serial (115200 baud)
           v
         ESP32
       /       \
  GPIO 18     GPIO 19
   LED 1       LED 2
```

## Hardware

- ESP32 development board
- 2 standard LEDs
- 2 resistors (220–330 Ω)
- USB data cable
- Computer running Python

### Wiring

| Component | Connection |
|---|---|
| LED 1 anode (+) | GPIO 18 through resistor |
| LED 1 cathode (−) | GND |
| LED 2 anode (+) | GPIO 19 through resistor |
| LED 2 cathode (−) | GND |

## Requirements

- Python 3.9+
- Arduino IDE
- ESP32 Arduino board support
- Flask
- pySerial

## Installation

### 1. Flash the ESP32

Upload the ESP32 firmware from your Arduino sketch. The firmware listens for serial commands at `115200` baud.

Supported commands:

- `LED1_ON`
- `LED1_OFF`
- `LED2_ON`
- `LED2_OFF`
- `STATUS`

Each command must end with a newline.

### 2. Install Python dependencies

```bash
python -m pip install flask pyserial
```

### 3. Configure the serial port

In `server.py`, set the port to match your ESP32:

```python
SERIAL_PORT = "COM3"  # Windows example
BAUD_RATE = 115200
```

Examples of port names:

- Windows: `COM3`, `COM4`
- macOS: `/dev/cu.usbserial-XXXX`
- Linux: `/dev/ttyUSB0` or `/dev/ttyACM0`

Close Arduino IDE's Serial Monitor before starting the Python server.

### 4. Start the server

```bash
python server.py
```

Open the web interface on the same computer:

http://127.0.0.1:5000

### 5. Access from your local network

The Flask server must bind to all interfaces:

```python
app.run(host="0.0.0.0", port=5000, debug=False)
```

Find your computer's local IP address, then open:

```text
http://YOUR_COMPUTER_IP:5000
```

For example, `http://192.168.1.50:5000`.

Ensure your firewall allows inbound connections to port 5000 on your trusted private network.

## REST API

Base URL:

```text
http://YOUR_COMPUTER_IP:5000
```

### Get LED status

**GET** `/api/status`

Example:

```bash
curl http://localhost:5000/api/status
```

Example response:

```json
{
  "response": "LED1=1 LED2=0"
}
```

`1` means ON; `0` means OFF.

### Set LED state

**POST** `/api/led/{led}`

Path parameter:

- `led`: LED number, either `1` or `2`.

JSON request body:

```json
{
  "state": "on"
}
```

Allowed states: `on`, `off`.

Example — turn on LED 1:

```bash
curl -X POST http://localhost:5000/api/led/1 \
  -H "Content-Type: application/json" \
  -d '{"state":"on"}'
```

Example — turn off LED 2:

```bash
curl -X POST http://localhost:5000/api/led/2 \
  -H "Content-Type: application/json" \
  -d '{"state":"off"}'
```

Example success response:

```json
{
  "led": 1,
  "state": "on",
  "response": "OK LED1 ON"
}
```

### HTTP status codes

| Code | Meaning |
|---|---|
| `200` | Request successful |
| `400` | Invalid LED number or state |
| `404` | Unknown route |
| `504` | No valid response from ESP32 |

## Project structure

```text
esp32-led-controller/
├── server.py
├── openapi.yaml
└── README.md
```

## Troubleshooting

**Serial port unavailable**
- Check the USB cable supports data.
- Verify the serial port in Arduino IDE.
- Close other programs using the port.

**LEDs do not respond**
- Confirm GPIO 18 and GPIO 19 wiring.
- Verify the ESP32 firmware has been uploaded.
- Check that the server is communicating at 115200 baud.

**Website inaccessible from another device**
- Confirm both devices are on the same reachable network.
- Use the computer's LAN IP instead of `127.0.0.1`.
- Check firewall rules and guest-network isolation.

**Serial communication times out**
- The ESP32 may reset when the serial port opens.
- Ensure the firmware is running and commands end with a newline.
- Check the USB cable and serial port settings.

## Security

This server is intended for trusted local networks. The API has no authentication, so anyone who can reach the server may control the LEDs. Do not expose port 5000 directly to the public internet.

## License

MIT — add a `LICENSE` file if you intend to distribute the project under this license.
