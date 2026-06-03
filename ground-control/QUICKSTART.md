# 🚀 Project Vyom - Ground Control Station Quick Start Guide

## 🎯 What You Have

A complete ground control station system for your Project Vyom rocket with:

- **Real-time telemetry display** with live data from your rocket
- **Advanced trajectory visualization** comparing actual vs theoretical flight paths
- **Comprehensive data logging** and analysis capabilities
- **Safety monitoring** with configurable limits and anomaly detection
- **Flight report generation** for post-mission analysis

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd ground-control
pip install -r requirements.txt
```

### 2. Test the System
```bash
python test_ground_control.py
```

### 3. Start Ground Control Station
```bash
# Basic startup
python start_ground_control.py

# With telemetry simulator (for testing)
python start_ground_control.py --simulate --port COM3
```

## 📡 Hardware Integration

### Serial Connection
Connect your rocket's avionics to the ground station via serial:

- **Port**: COM3 (Windows) or /dev/ttyUSB0 (Linux)
- **Baud Rate**: 115200
- **Data Format**: JSON telemetry packets

### Expected Telemetry Format
Your rocket's avionics should send JSON packets like:
```json
{
    "timestamp": "2024-01-01T12:00:00.000Z",
    "time": 5.2,
    "altitude": 150.5,
    "velocity": 45.2,
    "acceleration": 12.8,
    "latitude": -33.8688,
    "longitude": 151.2093,
    "roll": 2.1,
    "pitch": -1.5,
    "yaw": 0.8,
    "temperature": 35.2,
    "pressure": 98500.0,
    "thrust": 100,
    "battery_voltage": 12.4,
    "gps_fix": true,
    "tvc_angle": 1.2
}
```

## 🎮 Testing Without Hardware

Use the telemetry simulator to test the system:

```bash
# Run simulator separately
python telemetry_simulator.py --port COM3 --duration 120

# Or start ground control with simulator
python start_ground_control.py --simulate
```

## ⚙️ Configuration

Edit `config.json` to customize:

- **Rocket parameters**: Mass, thrust, burn time, etc.
- **Telemetry settings**: Port, baud rate, update intervals
- **Display settings**: Plot refresh rates, limits
- **Safety limits**: Maximum values for alerts
- **Mission profile**: Flight phase detection parameters

## 📊 Features Overview

### Real-time Display
- Live altitude, velocity, acceleration
- GPS coordinates and ground track
- Attitude (roll, pitch, yaw)
- Temperature, pressure, battery voltage
- Mission timeline with events

### Advanced Analysis
- Theoretical vs actual trajectory comparison
- Flight phase detection (boost, coast, descent)
- Anomaly detection and safety alerts
- Comprehensive flight statistics
- Post-mission report generation

### Data Management
- Automatic CSV logging
- Real-time data validation
- Export capabilities
- Configuration management

## 🔧 Customization

### Adding New Parameters
1. Update `TelemetryData` class in `ground_control_station.py`
2. Add display widgets in the status panel
3. Update telemetry parser for new fields
4. Add plotting if needed

### Hardware-Specific Adaptations
- Modify serial communication protocols
- Add support for different sensor types
- Implement custom data validation
- Add hardware-specific safety checks

## 🚨 Safety Features

- Real-time safety limit monitoring
- Automatic anomaly detection
- Mission success assessment
- Emergency alert system
- Data integrity validation

## 📁 File Structure

```
ground-control/
├── ground_control_station.py    # Main application
├── telemetry_simulator.py       # Testing simulator
├── trajectory_analyzer.py        # Analysis engine
├── config_manager.py           # Configuration handling
├── start_ground_control.py     # Startup script
├── test_ground_control.py      # Test suite
├── config.json                 # Configuration file
├── requirements.txt            # Dependencies
└── README.md                   # Full documentation
```

## 🆘 Troubleshooting

### Common Issues
1. **Serial connection fails**: Check port and baud rate settings
2. **No data received**: Verify telemetry format matches expected JSON
3. **Plots not updating**: Check data validation and parsing
4. **Configuration errors**: Verify JSON syntax in config.json

### Getting Help
- Check the full README.md for detailed documentation
- Run the test suite to verify installation
- Contact: 24adityasolanki24@gmail.com

---

**Ready to launch! 🚀** Your ground control station is now ready to receive telemetry from your Project Vyom rocket!
