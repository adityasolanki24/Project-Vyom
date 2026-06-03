#!/usr/bin/env python3
"""
Project Vyom - Configuration Manager
Handles loading and saving of configuration settings
"""

import json
import os
from typing import Dict, Any

class ConfigManager:
    """Manages configuration settings for the ground control station"""
    
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                # Return default configuration
                return self.get_default_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.get_default_config()
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "rocket_parameters": {
                "mass_initial": 0.5,
                "mass_fuel": 0.1,
                "mass_dry": 0.4,
                "thrust": 100,
                "burn_time": 2.0,
                "drag_coefficient": 0.01,
                "cross_sectional_area": 0.01,
                "exhaust_velocity": 300
            },
            "telemetry_settings": {
                "default_port": "COM3",
                "default_baud": 115200,
                "update_interval_ms": 100,
                "max_data_points": 10000,
                "log_format": "csv"
            },
            "display_settings": {
                "plot_refresh_rate": 10,
                "status_refresh_rate": 100,
                "timeline_max_entries": 100,
                "altitude_max": 1000,
                "velocity_max": 200,
                "time_window": 60
            },
            "safety_limits": {
                "max_altitude": 10000,
                "max_velocity": 500,
                "max_acceleration": 50,
                "min_battery_voltage": 3.0,
                "max_temperature": 80,
                "max_pressure": 120000
            },
            "mission_profile": {
                "launch_detection_threshold": 5.0,
                "apogee_detection_threshold": 1.0,
                "landing_detection_threshold": 2.0,
                "recovery_deployment_altitude": 100
            }
        }
    
    def get(self, section: str, key: str = None, default=None):
        """Get configuration value"""
        try:
            if key is None:
                return self.config.get(section, default)
            else:
                return self.config.get(section, {}).get(key, default)
        except Exception:
            return default
    
    def set(self, section: str, key: str, value: Any):
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def get_rocket_params(self) -> Dict[str, float]:
        """Get rocket parameters"""
        return self.get("rocket_parameters", default={})
    
    def get_telemetry_settings(self) -> Dict[str, Any]:
        """Get telemetry settings"""
        return self.get("telemetry_settings", default={})
    
    def get_display_settings(self) -> Dict[str, Any]:
        """Get display settings"""
        return self.get("display_settings", default={})
    
    def get_safety_limits(self) -> Dict[str, float]:
        """Get safety limits"""
        return self.get("safety_limits", default={})
    
    def get_mission_profile(self) -> Dict[str, float]:
        """Get mission profile"""
        return self.get("mission_profile", default={})
    
    def update_rocket_params(self, params: Dict[str, float]):
        """Update rocket parameters"""
        self.config["rocket_parameters"].update(params)
    
    def update_telemetry_settings(self, settings: Dict[str, Any]):
        """Update telemetry settings"""
        self.config["telemetry_settings"].update(settings)
    
    def update_display_settings(self, settings: Dict[str, Any]):
        """Update display settings"""
        self.config["display_settings"].update(settings)
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.config = self.get_default_config()
        self.save_config()
