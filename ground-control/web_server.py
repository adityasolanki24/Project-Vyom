#!/usr/bin/env python3
"""
Project Vyom - Web-based Ground Control Station Backend
FastAPI server with WebSocket support for real-time telemetry
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import csv
import json
import time
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
import uvicorn
from pathlib import Path
import logging

# Import our existing modules
import sys
sys.path.append(str(Path(__file__).parent.parent))
from telemetry_simulator import TelemetrySimulator
from config_manager import ConfigManager

try:
    from trajectory_analyzer import TrajectoryAnalyzer
except ImportError as exc:
    TrajectoryAnalyzer = None
    TRAJECTORY_ANALYZER_IMPORT_ERROR = exc
else:
    TRAJECTORY_ANALYZER_IMPORT_ERROR = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Project Vyom Ground Control Station API")

# Global variables
connected_clients: List[WebSocket] = []
config_manager = ConfigManager()
trajectory_analyzer = (
    TrajectoryAnalyzer(config_manager.get_rocket_params())
    if TrajectoryAnalyzer is not None
    else None
)
telemetry_simulator = TelemetrySimulator()
is_simulating = False
simulation_task = None
is_logging = False
log_filename = None
log_file_path = None
logged_packets: List[Dict[str, Any]] = []
flight_packets: List[Dict[str, Any]] = []

TELEMETRY_FIELDS = [
    "timestamp",
    "time",
    "altitude",
    "velocity",
    "acceleration",
    "latitude",
    "longitude",
    "roll",
    "pitch",
    "yaw",
    "temperature",
    "pressure",
    "thrust",
    "tvc_angle",
    "battery_voltage",
    "gps_fix",
    "flight_phase",
    "apogee_reached",
]

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "web_gui"
LOG_DIR = BASE_DIR / "logs"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def utc_timestamp() -> str:
    """Return a consistent ISO timestamp for API and WebSocket messages."""
    return datetime.now().isoformat()


def ws_message(message_type: str, data: Optional[Dict[str, Any]] = None, **legacy_fields) -> Dict[str, Any]:
    """Build the WebSocket envelope while retaining legacy top-level fields."""
    message = {
        "type": message_type,
        "data": data or {},
        "timestamp": utc_timestamp(),
    }
    message.update(legacy_fields)
    return message


def safe_log_path(filename: str) -> Path:
    """Keep log files inside the local logs directory."""
    candidate = Path(filename or "flight_data.csv").name
    if not candidate.lower().endswith(".csv"):
        candidate = f"{candidate}.csv"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / candidate


def write_log_header(path: Path):
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=TELEMETRY_FIELDS)
        writer.writeheader()


def append_packet_to_log(packet: Dict[str, Any]):
    if not log_file_path:
        return

    row = {field: packet.get(field, "") for field in TELEMETRY_FIELDS}
    with log_file_path.open("a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=TELEMETRY_FIELDS)
        writer.writerow(row)


def bounded_append(buffer: List[Dict[str, Any]], packet: Dict[str, Any]):
    buffer.append(packet.copy())
    max_points = config_manager.get_telemetry_settings().get("max_data_points", 10000)
    if len(buffer) > max_points:
        del buffer[: len(buffer) - max_points]


def number_or_none(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize_packets(packets: List[Dict[str, Any]]) -> Dict[str, Any]:
    safety_limits = config_manager.get_safety_limits()
    numeric = {
        "altitude": [number_or_none(p.get("altitude")) for p in packets],
        "velocity": [number_or_none(p.get("velocity")) for p in packets],
        "acceleration": [number_or_none(p.get("acceleration")) for p in packets],
        "temperature": [number_or_none(p.get("temperature")) for p in packets],
        "pressure": [number_or_none(p.get("pressure")) for p in packets],
        "battery_voltage": [number_or_none(p.get("battery_voltage")) for p in packets],
        "time": [number_or_none(p.get("time")) for p in packets],
    }

    def max_value(field: str, absolute: bool = False) -> float:
        values = [v for v in numeric[field] if v is not None]
        if not values:
            return 0
        if absolute:
            return max(abs(v) for v in values)
        return max(values)

    times = [v for v in numeric["time"] if v is not None]
    duration = max(times) - min(times) if len(times) >= 2 else 0
    max_altitude = max_value("altitude")
    max_velocity = max_value("velocity", absolute=True)
    max_acceleration = max_value("acceleration", absolute=True)
    apogee_packet = max(
        packets,
        key=lambda packet: number_or_none(packet.get("altitude")) or 0,
        default={},
    )

    anomalies = []
    seen = set()

    def add_anomaly(packet: Dict[str, Any], field: str, value: float, limit: float, severity: str):
        key = (field, severity)
        if key in seen:
            return
        seen.add(key)
        anomalies.append({
            "timestamp": packet.get("timestamp"),
            "field": field,
            "value": round(value, 3),
            "limit": limit,
            "severity": severity,
        })

    for packet in packets:
        checks = [
            ("altitude", "max_altitude", False),
            ("velocity", "max_velocity", True),
            ("acceleration", "max_acceleration", True),
            ("temperature", "max_temperature", False),
            ("pressure", "max_pressure", False),
        ]

        for field, limit_key, absolute in checks:
            value = number_or_none(packet.get(field))
            limit = number_or_none(safety_limits.get(limit_key))
            if value is None or limit is None:
                continue
            compare_value = abs(value) if absolute else value
            if compare_value >= limit:
                add_anomaly(packet, field, value, limit, "critical")

        battery = number_or_none(packet.get("battery_voltage"))
        min_battery = number_or_none(safety_limits.get("min_battery_voltage"))
        if battery is not None and min_battery is not None and battery <= min_battery:
            add_anomaly(packet, "battery_voltage", battery, min_battery, "critical")

        if packet.get("gps_fix") is False and ("gps_fix", "warning") not in seen:
            seen.add(("gps_fix", "warning"))
            anomalies.append({
                "timestamp": packet.get("timestamp"),
                "field": "gps_fix",
                "value": False,
                "limit": True,
                "severity": "warning",
            })

    return {
        "timestamp": utc_timestamp(),
        "data_points": len(packets),
        "max_altitude": round(max_altitude, 3),
        "max_velocity": round(max_velocity, 3),
        "max_acceleration": round(max_acceleration, 3),
        "flight_duration": round(duration, 3),
        "apogee": {
            "altitude": round(number_or_none(apogee_packet.get("altitude")) or 0, 3),
            "time": round(number_or_none(apogee_packet.get("time")) or 0, 3),
            "timestamp": apogee_packet.get("timestamp"),
        },
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "logging_active": is_logging,
        "log_file": str(log_file_path) if log_file_path else None,
    }

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

@app.get("/")
async def get_index():
    """Serve the main HTML page"""
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/api/status")
async def get_status():
    """Get current system status"""
    return {
        "connected_clients": len(manager.active_connections),
        "is_simulating": is_simulating,
        "is_logging": is_logging,
        "logging": {
            "active": is_logging,
            "filename": log_filename,
            "data_points": len(logged_packets),
            "log_file": str(log_file_path) if log_file_path else None,
        },
        "simulation": {
            "active": is_simulating,
            "data_points": len(flight_packets),
        },
        "config": {
            "rocket_params": config_manager.get_rocket_params(),
            "rocket_parameters": config_manager.get_rocket_params(),
            "telemetry_settings": config_manager.get_telemetry_settings(),
            "display_settings": config_manager.get_display_settings(),
            "safety_limits": config_manager.get_safety_limits(),
            "mission_profile": config_manager.get_mission_profile(),
        }
    }

@app.post("/api/simulation/start")
async def start_simulation():
    """Start telemetry simulation"""
    global is_simulating, simulation_task, telemetry_simulator, flight_packets
    
    if is_simulating:
        return {"status": "already_running"}
    
    telemetry_simulator = TelemetrySimulator()
    flight_packets = []
    is_simulating = True
    simulation_task = asyncio.create_task(run_simulation())
    
    await manager.broadcast(ws_message(
        "simulation_status",
        {"status": "started"},
        status="started",
    ))
    
    return {"status": "started"}

@app.post("/api/simulation/stop")
async def stop_simulation():
    """Stop telemetry simulation"""
    global is_simulating, simulation_task
    
    if not is_simulating:
        return {"status": "not_running"}
    
    is_simulating = False
    if simulation_task:
        simulation_task.cancel()
    
    await manager.broadcast(ws_message(
        "simulation_status",
        {"status": "stopped"},
        status="stopped",
    ))
    
    return {"status": "stopped"}

@app.post("/api/logging/start")
async def start_logging(filename: str = "flight_data.csv"):
    """Start data logging"""
    global is_logging, log_filename, log_file_path, logged_packets

    log_file_path = safe_log_path(filename)
    log_filename = log_file_path.name
    logged_packets = []
    write_log_header(log_file_path)
    is_logging = True

    await manager.broadcast(ws_message(
        "logging_status",
        {
            "status": "started",
            "filename": log_filename,
            "log_file": str(log_file_path),
        },
        status="started",
        filename=log_filename,
    ))
    
    return {"status": "started", "filename": log_filename, "log_file": str(log_file_path)}

@app.post("/api/logging/stop")
async def stop_logging():
    """Stop data logging"""
    global is_logging

    is_logging = False

    await manager.broadcast(ws_message(
        "logging_status",
        {
            "status": "stopped",
            "filename": log_filename,
            "data_points": len(logged_packets),
            "log_file": str(log_file_path) if log_file_path else None,
        },
        status="stopped",
        filename=log_filename,
    ))
    
    return {"status": "stopped", "filename": log_filename, "data_points": len(logged_packets)}

@app.post("/api/report/generate")
async def generate_report():
    """Generate flight report"""
    packets = logged_packets if logged_packets else flight_packets
    report = summarize_packets(packets)
    
    await manager.broadcast(ws_message(
        "report_generated",
        report,
        report=report,
    ))
    
    return report

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps(ws_message("pong", {"status": "ok"})))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

async def run_simulation():
    """Run telemetry simulation and broadcast data"""
    global is_simulating
    
    logger.info("Starting telemetry simulation")
    
    try:
        while is_simulating:
            # Generate simulated telemetry data
            packet = telemetry_simulator.generate_telemetry_packet()
            bounded_append(flight_packets, packet)

            if is_logging:
                bounded_append(logged_packets, packet)
                append_packet_to_log(packet)
            
            # Broadcast to all connected clients
            await manager.broadcast(ws_message("telemetry", packet))
            
            # Wait before next update
            await asyncio.sleep(0.1)  # 10 Hz update rate
            
    except asyncio.CancelledError:
        logger.info("Simulation cancelled")
    except Exception as e:
        logger.error(f"Simulation error: {e}")
    finally:
        is_simulating = False

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    logger.info("Project Vyom Ground Control Station API starting...")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global is_simulating, simulation_task
    
    logger.info("Shutting down Ground Control Station API...")
    
    # Stop simulation
    is_simulating = False
    if simulation_task:
        simulation_task.cancel()

def main():
    """Main function to run the server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Project Vyom Ground Control Station Web Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    logger.info(f"Starting server on http://{args.host}:{args.port}")
    
    uvicorn.run(
        "web_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )

if __name__ == "__main__":
    main()
