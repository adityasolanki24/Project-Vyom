# Project Vyom

## Overview

**Project Vyom** is an ongoing aerospace engineering project focused on the development of a guided sounding rocket platform integrating solid propulsion, active thrust vector control (TVC), and a modular avionics architecture.

The project combines propulsion design, embedded systems, flight control, telemetry, and structural design to build a scalable experimental launch system capable of autonomous flight stabilization and high-fidelity data acquisition.

The current development phase focuses on the **flight computer and data logging architecture**, including sensor fusion, onboard storage, and telemetry integration.

---

## Project Objectives

- Develop a stable and scalable solid rocket motor platform  
- Implement active thrust vector control using closed-loop feedback  
- Design a modular avionics and flight computer architecture  
- Enable reliable real-time flight data logging and telemetry  
- Validate system performance through incremental ground and flight testing  

---

## System Architecture

### 1. Avionics and Flight Computer

- Primary flight controller based on Teensy 4.1  
- Secondary real-time control MCU (STM32F4 series)  
- Sensor suite:
  - IMU (MPU9250 / BNO085)
  - GNSS receiver (u-blox)
  - Barometric altitude sensor (BMP388)
- Data logging to onboard SD storage
- LoRa telemetry link (under development)
- Modular firmware architecture supporting independent sensor and control modules
- Focus on synchronized high-rate data acquisition and event logging

**Current Development Focus**
- Flight data logging framework
- Sensor sampling pipeline
- Timestamp synchronization
- Fault-tolerant data storage

---

### 2. Thrust Vector Control (TVC)

- STM32F405/411 based real-time controller
- Servo-driven nozzle or gimbal actuation
- IMU feedback for attitude stabilization
- PID control loop with tunable gain scheduling
- High-speed communication interface with avionics subsystem (UART/SPI)

---

### 3. Propulsion System

- Solid propellant motor architecture
- Nozzle geometry modelling and simulation
- Burn profile and thrust estimation (Python / spreadsheet models)
- Static test stand design for thrust characterization (in progress)

---

### 4. Airframe and Structural Design

- Full rocket CAD design (SolidWorks / Fusion 360)
- Center of Gravity (CG) and Center of Pressure (CP) stability analysis
- Modular payload and avionics bay
- Configurable fin design
- Recovery subsystem under development

---

### 5. Testing and Ground Systems

- Static fire testing infrastructure
- Load-cell based thrust measurement system
- Ground telemetry receiver and logging interface
- Arm/disarm and launch safety architecture

---

## Development Milestones

| Milestone | Status |
|---|---|
| Solid motor design | Completed (outsourced) |
| Airframe CAD design | In progress |
| Flight computer data logging framework | In progress (current phase) |
| TVC rig testing | Pending |
| Telemetry ground station | In progress |
| First guided flight | Planned |

---

## Author

**Aditya Solanki**  
Mechatronics Engineering — University of Sydney  

**Areas of Focus**
- Embedded systems
- Flight control and guidance
- Aerospace systems engineering

---

## Project Name

“Vyom” (व्योम) refers to space or sky in Sanskrit, representing the long-term objective of developing advanced autonomous flight systems.

---

## Contact

Email: 24adityasolanki24@gmail.com  
LinkedIn: www.linkedin.com/in/aditya-solanki-6174a4289
