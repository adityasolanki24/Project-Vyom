import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import csv
import os
import time
from datetime import datetime

# Rocket parameters (adjust to your rocket's specs)
m0 = 0.5  # Initial mass (kg)
m_fuel = 0.1  # Fuel mass (kg)
m_dry = m0 - m_fuel
thrust = 100  # Thrust (N)
burn_time = 2.0  # Burn duration (s)
v_e = 300  # Exhaust velocity (m/s)
g = 9.81  # Gravity (m/s^2)
k = 0.01  # Drag coefficient (kg/m)

# Simulation parameters
dt = 0.1  # Time step (s)
t_max = 10.0  # Total simulation time (s)
t_sim = np.arange(0, t_max, dt)
n = len(t_sim)
altitude_sim = np.zeros(n)
velocity_sim = np.zeros(n)

# Simulate trajectory
for i in range(1, n):
    t_now = t_sim[i]
    m = m0 - (m_fuel / burn_time) * t_now if t_now <= burn_time else m_dry
    thrust_force = thrust if t_now <= burn_time else 0
    drag = k * velocity_sim[i-1]**2
    a = (thrust_force - drag - m * g) / m
    velocity_sim[i] = velocity_sim[i-1] + a * dt
    # Use current velocity for altitude calculation (more accurate)
    altitude_sim[i] = altitude_sim[i-1] + velocity_sim[i] * dt
    if altitude_sim[i] < 0:
        altitude_sim[i] = 0
        velocity_sim[i] = 0

# Real-time data setup
t_data = []
alt_data = []
csv_file = "telemetry.csv"  # Path to your sensor CSV
last_file_size = 0  # Track file size for efficient updates
last_update_time = 0  # Track last update time

# For testing: Simulate real-time telemetry if no CSV exists
if not os.path.exists(csv_file):
    print("No telemetry.csv found. Using simulated telemetry.")
    telemetry_sim = [
        [0.0, 0.0], [0.5, 10.2], [1.0, 40.5], [1.5, 90.3], [2.0, 150.1],
        [3.0, 200.8], [4.0, 220.5], [5.0, 210.2], [6.0, 150.7], [7.0, 50.3]
    ]
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["time", "altitude"])
        writer.writerows(telemetry_sim)

# Plot setup
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[3, 1])
fig.suptitle('Rocket Trajectory - Real-time vs Simulated', fontsize=14, fontweight='bold')

# Main trajectory plot
line_sim, = ax1.plot([], [], 'b-', label='Simulated Altitude', linewidth=2)
line_data, = ax1.plot([], [], 'r--', label='Telemetry Altitude', linewidth=2)
ax1.set_xlim(0, t_max)
ax1.set_ylim(0, float(np.max(altitude_sim)) * 1.2)
ax1.set_xlabel('Time (s)')
ax1.set_ylabel('Altitude (m)')
ax1.grid(True, alpha=0.3)
ax1.legend()

# Status text
status_text = ax1.text(0.02, 0.98, '', transform=ax1.transAxes, 
                      verticalalignment='top', fontsize=10,
                      bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

# Error plot (difference between simulated and actual)
line_error, = ax2.plot([], [], 'g-', label='Altitude Error', linewidth=1)
ax2.set_xlim(0, t_max)
ax2.set_ylim(-50, 50)
ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Error (m)')
ax2.grid(True, alpha=0.3)
ax2.legend()

plt.tight_layout()

def validate_telemetry_data(t_val, alt_val):
    """Validate telemetry data for reasonable values"""
    if not (0 <= t_val <= 60):  # Max 60 seconds
        return False
    if not (0 <= alt_val <= 10000):  # Max 10km altitude
        return False
    return True

# Animation update function
def update(frame):
    global last_file_size, last_update_time
    
    current_time = time.time()
    
    # Only read CSV if file has changed or enough time has passed
    try:
        current_file_size = os.path.getsize(csv_file)
        if current_file_size != last_file_size or (current_time - last_update_time) > 0.1:
            with open(csv_file, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                t_data.clear()
                alt_data.clear()
                for row in reader:
                    if len(row) >= 2:  # Ensure we have at least 2 columns
                        try:
                            t_val = float(row[0])
                            alt_val = float(row[1])
                            if validate_telemetry_data(t_val, alt_val):
                                t_data.append(t_val)
                                alt_data.append(alt_val)
                        except ValueError:
                            continue  # Skip malformed data
            last_file_size = current_file_size
            last_update_time = current_time
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    # Update simulated trajectory up to current frame
    frame_idx = min(frame, n-1)
    line_sim.set_data(t_sim[:frame_idx], altitude_sim[:frame_idx])
    
    # Update telemetry data
    line_data.set_data(t_data, alt_data)
    
    # Update y-axis limits if telemetry data exceeds current range
    if alt_data:
        max_alt = max(max(alt_data), float(np.max(altitude_sim)))
        ax1.set_ylim(0, max_alt * 1.2)
    
    # Calculate and plot error
    error_data = []
    error_times = []
    if t_data and alt_data:
        for i, t in enumerate(t_data):
            if t <= t_max:
                # Find closest simulated altitude
                sim_idx = min(int(t / dt), n-1)
                if sim_idx < len(altitude_sim):
                    error = alt_data[i] - altitude_sim[sim_idx]
                    error_data.append(error)
                    error_times.append(t)
    
    line_error.set_data(error_times, error_data)
    
    # Update status text
    status_info = []
    status_info.append(f"Current Time: {datetime.now().strftime('%H:%M:%S')}")
    if t_data:
        status_info.append(f"Latest Telemetry: {t_data[-1]:.1f}s, {alt_data[-1]:.1f}m")
        if len(t_data) > 1:
            # Calculate rate of change
            dt_telemetry = t_data[-1] - t_data[-2]
            dalt_telemetry = alt_data[-1] - alt_data[-2]
            if dt_telemetry > 0:
                velocity_telemetry = dalt_telemetry / dt_telemetry
                status_info.append(f"Current Velocity: {velocity_telemetry:.1f} m/s")
    status_info.append(f"Data Points: {len(t_data)}")
    
    status_text.set_text('\n'.join(status_info))
    
    return line_sim, line_data, line_error, status_text

# Create animation with more reasonable frame rate
ani = FuncAnimation(fig, update, frames=len(t_sim), interval=50, blit=True, repeat=False)
plt.show()