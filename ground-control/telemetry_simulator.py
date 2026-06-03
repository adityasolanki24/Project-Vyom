#!/usr/bin/env python3
"""
Project Vyom - Telemetry Simulator
Simulates rocket telemetry data for testing the ground control station
"""

import json
import time
import math
import random
import argparse
from datetime import datetime

try:
    import serial
except ImportError:
    serial = None

class TelemetrySimulator:
    """Simulates rocket telemetry data"""
    
    def __init__(self, port=None, baud=115200):
        self.port = port
        self.baud = baud
        self.serial_connection = None
        
        # Simulation parameters
        self.start_time = time.time()
        self.flight_phase = "pre_launch"  # pre_launch, boost, coast, descent, landed
        self.apogee_reached = False
        
        # Rocket parameters
        self.mass_initial = 0.5  # kg
        self.mass_fuel = 0.1     # kg
        self.thrust = 100        # N
        self.burn_time = 2.0     # s
        self.drag_coefficient = 0.01
        
        # State variables
        self.altitude = 0.0
        self.velocity = 0.0
        self.acceleration = 0.0
        self.latitude = -33.8688  # Sydney coordinates
        self.longitude = 151.2093
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.temperature = 25.0
        self.pressure = 101325.0
        self.battery_voltage = 12.6
        self.gps_fix = True
        self.tvc_angle = 0.0
        
        # Launch detection
        self.launch_detected = False
        self.launch_time = None
        
    def connect_serial(self):
        """Connect to serial port for output"""
        if self.port:
            if serial is None:
                print("pyserial is not installed; continuing without serial output")
                return False
            try:
                self.serial_connection = serial.Serial(self.port, self.baud, timeout=1)
                print(f"Connected to {self.port} at {self.baud} baud")
                return True
            except Exception as e:
                print(f"Failed to connect to {self.port}: {e}")
                return False
        return False
    
    def simulate_flight_physics(self, elapsed_time):
        """Simulate rocket flight physics"""
        g = 9.81  # Gravity
        
        # Determine flight phase
        if elapsed_time < 5.0:
            self.flight_phase = "pre_launch"
        elif elapsed_time < 5.0 + self.burn_time:
            self.flight_phase = "boost"
        elif self.velocity > 0:
            self.flight_phase = "coast"
        elif self.altitude > 5.0:
            self.flight_phase = "descent"
        else:
            self.flight_phase = "landed"
        
        # Calculate mass (fuel consumption)
        if self.flight_phase == "boost":
            fuel_consumed = (elapsed_time - 5.0) * (self.mass_fuel / self.burn_time)
            mass = self.mass_initial - fuel_consumed
        else:
            mass = self.mass_initial - self.mass_fuel
        
        # Calculate thrust
        if self.flight_phase == "boost":
            thrust_force = self.thrust
        else:
            thrust_force = 0
        
        # Calculate drag
        drag_force = self.drag_coefficient * self.velocity**2
        
        # Calculate acceleration
        if self.flight_phase == "pre_launch":
            self.acceleration = 0
        else:
            self.acceleration = (thrust_force - drag_force - mass * g) / mass
        
        # Update velocity and altitude
        dt = 0.1  # Time step
        self.velocity += self.acceleration * dt
        
        if self.flight_phase != "pre_launch":
            self.altitude += self.velocity * dt
        
        # Ensure altitude doesn't go negative
        if self.altitude < 0:
            self.altitude = 0
            self.velocity = 0
        
        # Detect apogee
        if self.velocity < 0 and not self.apogee_reached and self.altitude > 50:
            self.apogee_reached = True
            print(f"Apogee reached at {self.altitude:.1f}m")
    
    def simulate_sensors(self, elapsed_time):
        """Simulate sensor readings with realistic noise and drift"""
        # GPS simulation
        if self.flight_phase == "pre_launch":
            # Small random walk for GPS
            self.latitude += random.uniform(-0.00001, 0.00001)
            self.longitude += random.uniform(-0.00001, 0.00001)
        else:
            # Simulate GPS drift during flight
            drift_factor = min(elapsed_time / 10.0, 1.0)
            self.latitude += random.uniform(-0.0001, 0.0001) * drift_factor
            self.longitude += random.uniform(-0.0001, 0.0001) * drift_factor
        
        # Attitude simulation
        if self.flight_phase == "boost":
            # Simulate rocket rotation during boost
            self.roll += random.uniform(-2, 2)
            self.pitch += random.uniform(-1, 1)
            self.yaw += random.uniform(-0.5, 0.5)
        else:
            # Tumbling during coast/descent
            self.roll += random.uniform(-5, 5)
            self.pitch += random.uniform(-3, 3)
            self.yaw += random.uniform(-2, 2)
        
        # Temperature simulation
        if self.flight_phase == "boost":
            self.temperature += random.uniform(0, 2)  # Heating during boost
        else:
            self.temperature += random.uniform(-0.5, 0.5)  # Cooling
        
        # Pressure simulation (altitude-based)
        altitude_pressure = 101325 * math.exp(-self.altitude / 8000)
        self.pressure = altitude_pressure + random.uniform(-100, 100)
        
        # Battery voltage simulation
        if elapsed_time > 5.0:  # After launch
            self.battery_voltage -= random.uniform(0.01, 0.05)
        
        # TVC angle simulation
        if self.flight_phase == "boost":
            self.tvc_angle = random.uniform(-5, 5)  # Active control
        else:
            self.tvc_angle = 0
        
        # GPS fix simulation
        if random.random() < 0.95:  # 95% fix rate
            self.gps_fix = True
        else:
            self.gps_fix = False
    
    def generate_telemetry_packet(self):
        """Generate a complete telemetry packet"""
        elapsed_time = time.time() - self.start_time
        
        # Update physics and sensors
        self.simulate_flight_physics(elapsed_time)
        self.simulate_sensors(elapsed_time)
        
        # Create telemetry packet
        packet = {
            "timestamp": datetime.now().isoformat(),
            "time": elapsed_time,
            "altitude": round(self.altitude, 2),
            "velocity": round(self.velocity, 2),
            "acceleration": round(self.acceleration, 2),
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "roll": round(self.roll, 1),
            "pitch": round(self.pitch, 1),
            "yaw": round(self.yaw, 1),
            "temperature": round(self.temperature, 1),
            "pressure": round(self.pressure, 1),
            "thrust": self.thrust if self.flight_phase == "boost" else 0,
            "battery_voltage": round(self.battery_voltage, 2),
            "gps_fix": self.gps_fix,
            "tvc_angle": round(self.tvc_angle, 1),
            "flight_phase": self.flight_phase,
            "apogee_reached": self.apogee_reached
        }
        
        return packet
    
    def run_simulation(self, duration=120):
        """Run the telemetry simulation"""
        print(f"Starting telemetry simulation for {duration} seconds...")
        print("Press Ctrl+C to stop")
        
        try:
            while time.time() - self.start_time < duration:
                packet = self.generate_telemetry_packet()
                
                # Print to console
                print(f"[{packet['time']:.1f}s] Alt: {packet['altitude']:.1f}m, "
                      f"Vel: {packet['velocity']:.1f}m/s, Phase: {packet['flight_phase']}")
                
                # Send to serial port
                if self.serial_connection:
                    json_data = json.dumps(packet) + '\n'
                    self.serial_connection.write(json_data.encode())
                
                # Write to file
                with open("telemetry_sim.csv", "a") as f:
                    if packet['time'] == 0:
                        f.write(",".join(packet.keys()) + "\n")
                    f.write(",".join(str(v) for v in packet.values()) + "\n")
                
                time.sleep(0.1)  # 10 Hz update rate
                
        except KeyboardInterrupt:
            print("\nSimulation stopped by user")
        finally:
            if self.serial_connection:
                self.serial_connection.close()
            print("Simulation complete")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Project Vyom Telemetry Simulator")
    parser.add_argument("--port", help="Serial port for output (e.g., COM3, /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--duration", type=int, default=120, help="Simulation duration in seconds")
    
    args = parser.parse_args()
    
    simulator = TelemetrySimulator(args.port, args.baud)
    
    if args.port:
        if not simulator.connect_serial():
            print("Continuing without serial output...")
    
    simulator.run_simulation(args.duration)

if __name__ == "__main__":
    main()
