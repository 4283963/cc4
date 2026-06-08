import numpy as np
from dataclasses import dataclass, field
from typing import Tuple, List


@dataclass
class VehicleParams:
    vehicle_id: int
    initial_velocity: float
    acceleration: float
    length: float
    width: float
    start_x: float
    start_y: float
    direction: float
    velocity_noise_std: float = 0.0
    acceleration_noise_std: float = 0.0
    position_noise_std: float = 0.0


@dataclass
class VehicleState:
    x: float
    y: float
    v: float
    a: float
    theta: float
    length: float
    width: float


def vehicle_position_at_time(params: VehicleParams, t: float, 
                             v_noise: float = 0.0, 
                             a_noise: float = 0.0,
                             pos_noise: np.ndarray = None) -> Tuple[float, float, float]:
    v0 = params.initial_velocity + v_noise
    a = params.acceleration + a_noise
    
    v = v0 + a * t
    if v < 0:
        v = 0
        a = 0
    
    dx = v0 * t + 0.5 * a * t**2
    
    theta = np.radians(params.direction)
    x = params.start_x + dx * np.cos(theta)
    y = params.start_y + dx * np.sin(theta)
    
    if pos_noise is not None:
        x += pos_noise[0]
        y += pos_noise[1]
    
    return x, y, v


def generate_vehicle_noise(params: VehicleParams, rng: np.random.Generator) -> dict:
    v_noise = rng.normal(0, params.velocity_noise_std) if params.velocity_noise_std > 0 else 0.0
    a_noise = rng.normal(0, params.acceleration_noise_std) if params.acceleration_noise_std > 0 else 0.0
    pos_noise = None
    if params.position_noise_std > 0:
        pos_noise = rng.normal(0, params.position_noise_std, size=2)
    return {
        'v_noise': v_noise,
        'a_noise': a_noise,
        'pos_noise': pos_noise
    }


def get_vehicle_corners(x: float, y: float, theta: float, 
                        length: float, width: float) -> np.ndarray:
    half_l = length / 2.0
    half_w = width / 2.0
    
    corners_local = np.array([
        [half_l, half_w],
        [half_l, -half_w],
        [-half_l, -half_w],
        [-half_l, half_w]
    ])
    
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    rot_matrix = np.array([
        [cos_t, -sin_t],
        [sin_t, cos_t]
    ])
    
    corners_world = corners_local @ rot_matrix.T + np.array([x, y])
    return corners_world


def get_vehicle_state(params: VehicleParams, t: float, noise: dict = None) -> VehicleState:
    if noise is None:
        noise = {'v_noise': 0.0, 'a_noise': 0.0, 'pos_noise': None}
    
    x, y, v = vehicle_position_at_time(
        params, t, 
        v_noise=noise['v_noise'],
        a_noise=noise['a_noise'],
        pos_noise=noise['pos_noise']
    )
    
    return VehicleState(
        x=x, y=y, v=v,
        a=params.acceleration + noise.get('a_noise', 0.0),
        theta=np.radians(params.direction),
        length=params.length,
        width=params.width
    )
