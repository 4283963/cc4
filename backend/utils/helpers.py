import json
import numpy as np
from typing import List
from ..core.vehicle import VehicleParams


def params_to_dict(params: VehicleParams) -> dict:
    return {
        'vehicle_id': params.vehicle_id,
        'initial_velocity': params.initial_velocity,
        'acceleration': params.acceleration,
        'length': params.length,
        'width': params.width,
        'start_x': params.start_x,
        'start_y': params.start_y,
        'direction': params.direction,
        'velocity_noise_std': params.velocity_noise_std,
        'acceleration_noise_std': params.acceleration_noise_std,
        'position_noise_std': params.position_noise_std
    }


def dict_to_params(data: dict) -> VehicleParams:
    return VehicleParams(
        vehicle_id=data.get('vehicle_id', 0),
        initial_velocity=data.get('initial_velocity', 10.0),
        acceleration=data.get('acceleration', 0.0),
        length=data.get('length', 4.5),
        width=data.get('width', 2.0),
        start_x=data.get('start_x', 0.0),
        start_y=data.get('start_y', 0.0),
        direction=data.get('direction', 0.0),
        velocity_noise_std=data.get('velocity_noise_std', 0.0),
        acceleration_noise_std=data.get('acceleration_noise_std', 0.0),
        position_noise_std=data.get('position_noise_std', 0.0)
    )


def format_collision_probability(p: float) -> str:
    if p < 0.0001:
        return f"{p*100:.4f}%"
    elif p < 0.01:
        return f"{p*100:.2f}%"
    else:
        return f"{p*100:.1f}%"


def generate_default_vehicles() -> List[dict]:
    return [
        {
            'id': 0,
            'initial_velocity': 12.0,
            'acceleration': -1.0,
            'length': 4.5,
            'width': 2.0,
            'start_x': -30.0,
            'start_y': 0.0,
            'direction': 0.0,
            'velocity_noise_std': 0.5,
            'acceleration_noise_std': 0.2,
            'position_noise_std': 0.1
        },
        {
            'id': 1,
            'initial_velocity': 10.0,
            'acceleration': 0.5,
            'length': 5.0,
            'width': 2.2,
            'start_x': 0.0,
            'start_y': -25.0,
            'direction': 90.0,
            'velocity_noise_std': 0.5,
            'acceleration_noise_std': 0.2,
            'position_noise_std': 0.1
        }
    ]
