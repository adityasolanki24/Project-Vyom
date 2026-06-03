#!/usr/bin/env python3
"""
Project Vyom - Trajectory Analysis Module
Advanced trajectory calculations and analysis for rocket flight data
"""

import numpy as np
import pandas as pd
from scipy import integrate, interpolate
from typing import Tuple, List, Dict, Any
import math

class TrajectoryAnalyzer:
    """Advanced trajectory analysis for rocket flight data"""
    
    def __init__(self, rocket_params: Dict[str, float]):
        self.rocket_params = rocket_params
        self.g = 9.81  # Gravity constant
        self.earth_radius = 6371000  # Earth radius in meters
    
    def calculate_theoretical_trajectory(self, time_points: np.ndarray) -> Dict[str, np.ndarray]:
        """Calculate theoretical trajectory based on rocket parameters"""
        n_points = len(time_points)
        
        # Initialize arrays
        altitude = np.zeros(n_points)
        velocity = np.zeros(n_points)
        acceleration = np.zeros(n_points)
        mass = np.zeros(n_points)
        thrust = np.zeros(n_points)
        
        # Rocket parameters
        m0 = self.rocket_params['mass_initial']
        m_fuel = self.rocket_params['mass_fuel']
        thrust_max = self.rocket_params['thrust']
        burn_time = self.rocket_params['burn_time']
        drag_coeff = self.rocket_params['drag_coefficient']
        
        dt = time_points[1] - time_points[0] if len(time_points) > 1 else 0.1
        
        for i in range(1, n_points):
            t = time_points[i]
            
            # Mass calculation
            if t <= burn_time:
                mass[i] = m0 - (m_fuel / burn_time) * t
                thrust[i] = thrust_max
            else:
                mass[i] = m0 - m_fuel
                thrust[i] = 0
            
            # Drag force
            drag_force = drag_coeff * velocity[i-1]**2
            
            # Acceleration
            if mass[i] > 0:
                acceleration[i] = (thrust[i] - drag_force - mass[i] * self.g) / mass[i]
            else:
                acceleration[i] = -self.g
            
            # Velocity and altitude
            velocity[i] = velocity[i-1] + acceleration[i] * dt
            altitude[i] = altitude[i-1] + velocity[i] * dt
            
            # Ensure altitude doesn't go negative
            if altitude[i] < 0:
                altitude[i] = 0
                velocity[i] = 0
        
        return {
            'time': time_points,
            'altitude': altitude,
            'velocity': velocity,
            'acceleration': acceleration,
            'mass': mass,
            'thrust': thrust
        }
    
    def analyze_flight_phases(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze different phases of the flight"""
        if df.empty:
            return {}
        
        phases = {
            'pre_launch': {'start': 0, 'end': 0},
            'boost': {'start': 0, 'end': 0},
            'coast': {'start': 0, 'end': 0},
            'descent': {'start': 0, 'end': 0},
            'landed': {'start': 0, 'end': 0}
        }
        
        # Detect launch (significant acceleration)
        launch_threshold = self.rocket_params.get('launch_detection_threshold', 5.0)
        launch_idx = None
        if 'acceleration' in df.columns:
            launch_idx = df[df['acceleration'] > launch_threshold].index[0] if len(df[df['acceleration'] > launch_threshold]) > 0 else None
        
        if launch_idx is not None:
            phases['pre_launch']['end'] = df.iloc[launch_idx]['time']
            phases['boost']['start'] = df.iloc[launch_idx]['time']
        
        # Detect end of boost (thrust cutoff)
        burn_time = self.rocket_params.get('burn_time', 2.0)
        if launch_idx is not None:
            boost_end_time = df.iloc[launch_idx]['time'] + burn_time
            boost_end_idx = df[df['time'] >= boost_end_time].index[0] if len(df[df['time'] >= boost_end_time]) > 0 else len(df) - 1
            phases['boost']['end'] = df.iloc[boost_end_idx]['time']
            phases['coast']['start'] = df.iloc[boost_end_idx]['time']
        
        # Detect apogee (velocity = 0)
        if 'velocity' in df.columns:
            apogee_idx = None
            for i in range(len(df) - 1):
                if df.iloc[i]['velocity'] > 0 and df.iloc[i+1]['velocity'] <= 0:
                    apogee_idx = i
                    break
            
            if apogee_idx is not None:
                phases['coast']['end'] = df.iloc[apogee_idx]['time']
                phases['descent']['start'] = df.iloc[apogee_idx]['time']
        
        # Detect landing (altitude near ground)
        if 'altitude' in df.columns:
            landing_threshold = self.rocket_params.get('landing_detection_threshold', 2.0)
            landing_idx = None
            for i in range(len(df) - 1, -1, -1):
                if df.iloc[i]['altitude'] <= landing_threshold:
                    landing_idx = i
                    break
            
            if landing_idx is not None:
                phases['descent']['end'] = df.iloc[landing_idx]['time']
                phases['landed']['start'] = df.iloc[landing_idx]['time']
        
        return phases
    
    def calculate_flight_statistics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive flight statistics"""
        if df.empty:
            return {}
        
        stats = {}
        
        # Basic statistics
        if 'altitude' in df.columns:
            stats['max_altitude'] = df['altitude'].max()
            stats['final_altitude'] = df['altitude'].iloc[-1]
        
        if 'velocity' in df.columns:
            stats['max_velocity'] = df['velocity'].max()
            stats['final_velocity'] = df['velocity'].iloc[-1]
        
        if 'acceleration' in df.columns:
            stats['max_acceleration'] = df['acceleration'].max()
            stats['min_acceleration'] = df['acceleration'].min()
        
        # Flight duration
        if 'time' in df.columns:
            stats['flight_duration'] = df['time'].max()
        
        # Apogee analysis
        if 'velocity' in df.columns and 'altitude' in df.columns:
            apogee_idx = df['velocity'].idxmax()
            if apogee_idx is not None:
                stats['apogee_time'] = df.iloc[apogee_idx]['time']
                stats['apogee_altitude'] = df.iloc[apogee_idx]['altitude']
        
        # Range calculation (if GPS data available)
        if 'latitude' in df.columns and 'longitude' in df.columns:
            stats['ground_range'] = self.calculate_ground_range(df)
        
        # Energy analysis
        if 'velocity' in df.columns and 'altitude' in df.columns:
            stats['max_kinetic_energy'] = 0.5 * self.rocket_params['mass_initial'] * df['velocity'].max()**2
            stats['max_potential_energy'] = self.rocket_params['mass_initial'] * self.g * df['altitude'].max()
        
        return stats
    
    def calculate_ground_range(self, df: pd.DataFrame) -> float:
        """Calculate ground range from GPS coordinates"""
        if 'latitude' not in df.columns or 'longitude' not in df.columns:
            return 0.0
        
        # Get start and end positions
        start_lat = df['latitude'].iloc[0]
        start_lon = df['longitude'].iloc[0]
        end_lat = df['latitude'].iloc[-1]
        end_lon = df['longitude'].iloc[-1]
        
        # Haversine formula for distance
        lat1_rad = math.radians(start_lat)
        lat2_rad = math.radians(end_lat)
        delta_lat = math.radians(end_lat - start_lat)
        delta_lon = math.radians(end_lon - start_lon)
        
        a = (math.sin(delta_lat / 2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return self.earth_radius * c
    
    def detect_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect anomalies in flight data"""
        anomalies = []
        
        # Check for unrealistic values
        safety_limits = {
            'max_altitude': 10000,
            'max_velocity': 500,
            'max_acceleration': 50,
            'min_battery_voltage': 3.0,
            'max_temperature': 80
        }
        
        for param, limit in safety_limits.items():
            if param in df.columns:
                if param.startswith('max_'):
                    exceeded = df[df[param] > limit]
                else:
                    exceeded = df[df[param] < limit]
                
                if not exceeded.empty:
                    anomalies.append({
                        'type': 'safety_limit_exceeded',
                        'parameter': param,
                        'limit': limit,
                        'count': len(exceeded),
                        'times': exceeded['time'].tolist() if 'time' in df.columns else []
                    })
        
        # Check for data gaps
        if 'time' in df.columns:
            time_diffs = df['time'].diff()
            large_gaps = time_diffs[time_diffs > 1.0]  # Gaps larger than 1 second
            
            if not large_gaps.empty:
                anomalies.append({
                    'type': 'data_gap',
                    'count': len(large_gaps),
                    'gaps': large_gaps.tolist()
                })
        
        return anomalies
    
    def generate_flight_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate comprehensive flight report"""
        report = {
            'flight_phases': self.analyze_flight_phases(df),
            'statistics': self.calculate_flight_statistics(df),
            'anomalies': self.detect_anomalies(df),
            'rocket_parameters': self.rocket_params,
            'data_points': len(df),
            'flight_success': True
        }
        
        # Determine flight success
        if report['anomalies']:
            report['flight_success'] = False
        
        if report['statistics'].get('max_altitude', 0) < 10:
            report['flight_success'] = False
        
        return report
    
    def interpolate_trajectory(self, df: pd.DataFrame, new_time_points: np.ndarray) -> pd.DataFrame:
        """Interpolate trajectory data to new time points"""
        if df.empty or 'time' not in df.columns:
            return pd.DataFrame()
        
        # Create interpolation functions for each parameter
        interpolated_data = {'time': new_time_points}
        
        for column in df.columns:
            if column != 'time' and df[column].dtype in ['float64', 'int64']:
                try:
                    f = interpolate.interp1d(df['time'], df[column], 
                                          kind='linear', bounds_error=False, 
                                          fill_value='extrapolate')
                    interpolated_data[column] = f(new_time_points)
                except Exception:
                    # If interpolation fails, use nearest value
                    interpolated_data[column] = np.interp(new_time_points, df['time'], df[column])
        
        return pd.DataFrame(interpolated_data)
    
    def calculate_trajectory_accuracy(self, actual_df: pd.DataFrame, 
                                    theoretical_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate accuracy metrics comparing actual vs theoretical trajectory"""
        if actual_df.empty or theoretical_df.empty:
            return {}
        
        # Interpolate theoretical data to match actual time points
        if 'time' in actual_df.columns and 'time' in theoretical_df.columns:
            theoretical_interp = self.interpolate_trajectory(theoretical_df, actual_df['time'].values)
        else:
            return {}
        
        accuracy_metrics = {}
        
        # Calculate RMSE for each parameter
        for param in ['altitude', 'velocity', 'acceleration']:
            if param in actual_df.columns and param in theoretical_interp.columns:
                actual_values = actual_df[param].values
                theoretical_values = theoretical_interp[param].values
                
                # Remove NaN values
                mask = ~(np.isnan(actual_values) | np.isnan(theoretical_values))
                if np.any(mask):
                    rmse = np.sqrt(np.mean((actual_values[mask] - theoretical_values[mask])**2))
                    accuracy_metrics[f'{param}_rmse'] = rmse
                    
                    # Calculate relative error
                    max_theoretical = np.max(np.abs(theoretical_values[mask]))
                    if max_theoretical > 0:
                        accuracy_metrics[f'{param}_relative_error'] = rmse / max_theoretical
        
        return accuracy_metrics
