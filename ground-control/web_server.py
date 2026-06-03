#!/usr/bin/env python3
"""
Project Vyom - Web-based Ground Control Station Backend
FastAPI server with WebSocket support for real-time telemetry
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import json
import time
import threading
from datetime import datetime
from typing import List, Dict, Any
import uvicorn
from pathlib import Path
import logging

# Import our existing modules
import sys
sys.path.append(str(Path(__file__).parent.parent))
from telemetry_simulator import TelemetrySimulator
from trajectory_analyzer import TrajectoryAnalyzer
from config_manager import ConfigManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Project Vyom Ground Control Station API")

# Global variables
connected_clients: List[WebSocket] = []
config_manager = ConfigManager()
trajectory_analyzer = TrajectoryAnalyzer(config_manager.get_rocket_params())
telemetry_simulator = TelemetrySimulator()
is_simulating = False
simulation_task = None

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
    return FileResponse("web_gui/index.html")

@app.get("/api/status")
async def get_status():
    """Get current system status"""
    return {
        "connected_clients": len(manager.active_connections),
        "is_simulating": is_simulating,
        "config": {
            "rocket_params": config_manager.get_rocket_params(),
            "telemetry_settings": config_manager.get_telemetry_settings()
        }
    }

@app.post("/api/simulation/start")
async def start_simulation():
    """Start telemetry simulation"""
    global is_simulating, simulation_task
    
    if is_simulating:
        return {"status": "already_running"}
    
    is_simulating = True
    simulation_task = asyncio.create_task(run_simulation())
    
    await manager.broadcast({
        "type": "simulation_status",
        "status": "started",
        "timestamp": datetime.now().isoformat()
    })
    
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
    
    await manager.broadcast({
        "type": "simulation_status",
        "status": "stopped",
        "timestamp": datetime.now().isoformat()
    })
    
    return {"status": "stopped"}

@app.post("/api/logging/start")
async def start_logging(filename: str = "flight_data.csv"):
    """Start data logging"""
    # In a real implementation, this would start logging to file
    await manager.broadcast({
        "type": "logging_status",
        "status": "started",
        "filename": filename,
        "timestamp": datetime.now().isoformat()
    })
    
    return {"status": "started", "filename": filename}

@app.post("/api/logging/stop")
async def stop_logging():
    """Stop data logging"""
    await manager.broadcast({
        "type": "logging_status",
        "status": "stopped",
        "timestamp": datetime.now().isoformat()
    })
    
    return {"status": "stopped"}

@app.post("/api/report/generate")
async def generate_report():
    """Generate flight report"""
    # This would analyze current telemetry data and generate a report
    report = {
        "timestamp": datetime.now().isoformat(),
        "data_points": 0,  # Would be actual count
        "max_altitude": 0,
        "max_velocity": 0,
        "flight_duration": 0,
        "anomalies": []
    }
    
    await manager.broadcast({
        "type": "report_generated",
        "report": report,
        "timestamp": datetime.now().isoformat()
    })
    
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
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))
            
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
            
            # Broadcast to all connected clients
            await manager.broadcast({
                "type": "telemetry",
                "data": packet,
                "timestamp": datetime.now().isoformat()
            })
            
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
    
    # Mount static files
    static_path = Path(__file__).parent / "web_gui"
    app.mount("/static", StaticFiles(directory=static_path), name="static")

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
