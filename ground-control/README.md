# Project Vyom Ground Control

Mission-operations web console for Project Vyom, an experimental guided model rocket with active thrust vector control, parachute recovery, and live telemetry monitoring.

## Run

```bash
cd ground-control
pip install -r requirements.txt
python web_server.py --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. The frontend is static HTML/CSS/ES modules in `web_gui/`; no build step is required.

## REST And WebSocket Contract

The server keeps the existing WebSocket at `ws://<host>:8000/ws`. Broadcast messages use:

```json
{ "type": "telemetry", "data": {}, "timestamp": "2026-06-03T00:00:00" }
```

Current message types are `telemetry`, `simulation_status`, `logging_status`, `report_generated`, and `pong`. The client sends `{ "type": "ping" }` for heartbeat.

Preserved REST endpoints:

- `GET /api/status`
- `POST /api/simulation/start`
- `POST /api/simulation/stop`
- `POST /api/logging/start`
- `POST /api/logging/stop`
- `POST /api/report/generate`

`/api/status` returns the full display, safety, telemetry, and mission profile sections from `config.json`. Logging writes CSV rows under `logs/`, and report generation summarizes real packets from the active log or current simulation session.

## Telemetry Packet Schema

Each `telemetry.data` packet is expected to contain:

```json
{
  "timestamp": "ISO string",
  "time": 0.0,
  "altitude": 0.0,
  "velocity": 0.0,
  "acceleration": 0.0,
  "latitude": -33.8688,
  "longitude": 151.2093,
  "roll": 0.0,
  "pitch": 0.0,
  "yaw": 0.0,
  "temperature": 25.0,
  "pressure": 101325.0,
  "thrust": 0.0,
  "tvc_angle": 0.0,
  "battery_voltage": 12.6,
  "gps_fix": true,
  "flight_phase": "pre_launch",
  "apogee_reached": false
}
```

The UI treats every field as optional and shows `--` plus stale/LOS state instead of crashing.

## Future Telemetry Sources

Frontend telemetry is isolated in `web_gui/js/telemetry-source.js`.

- `WebSocketTelemetrySource` is active now and consumes the simulator through `/ws`.
- `SerialUsbTelemetrySource` is a documented TODO for Teensy 4.1 JSON-per-line packets. Defaults come from `config.json`: `telemetry_settings.default_port` (`COM3`) and `telemetry_settings.default_baud` (`115200`).
- `LoraBackendTelemetrySource` is a documented TODO for a backend LoRa relay.

Both future sources should normalize packets in the backend and publish the same WebSocket envelope and telemetry schema, so UI components do not need to change.
