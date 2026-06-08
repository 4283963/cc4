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
    road_condition: str = 'dry_asphalt'
    mass: float = 1500.0
    gravity: float = 9.81


@dataclass
class VehicleState:
    x: float
    y: float
    v: float
    a: float
    theta: float
    length: float
    width: float


def get_friction_coeff(road_condition: str, velocity: float = 0.0) -> float:
    from .tire_model import get_road_condition, compute_effective_friction
    road = get_road_condition(road_condition)
    return compute_effective_friction(velocity, road)


def get_max_acceleration(road_condition: str, velocity: float = 0.0,
                         braking: bool = True) -> float:
    mu = get_friction_coeff(road_condition, velocity)
    return mu * 9.81


def clamp_acceleration(requested_accel: float, road_condition: str,
                       velocity: float) -> float:
    if velocity <= 0:
        mu = get_friction_coeff(road_condition, 0.1)
    else:
        mu = get_friction_coeff(road_condition, velocity)
    
    max_brake = -mu * 9.81
    max_drive = mu * 9.81 * 0.6
    
    if requested_accel < max_brake:
        return max_brake
    elif requested_accel > max_drive:
        return max_drive
    return requested_accel


def vehicle_position_at_time(params: VehicleParams, t: float, 
                             v_noise: float = 0.0, 
                             a_noise: float = 0.0,
                             pos_noise: np.ndarray = None) -> Tuple[float, float, float, float]:
    if t <= 0:
        v0 = params.initial_velocity + v_noise
        theta = np.radians(params.direction)
        x = params.start_x
        y = params.start_y
        if pos_noise is not None:
            x += pos_noise[0]
            y += pos_noise[1]
        return x, y, v0, params.acceleration + a_noise
    
    dt_step = 0.01
    num_steps = int(t / dt_step) + 1
    
    v = params.initial_velocity + v_noise
    x = params.start_x
    y = params.start_y
    a = params.acceleration + a_noise
    theta = np.radians(params.direction)
    
    actual_a = a
    
    for i in range(num_steps):
        current_t = i * dt_step
        
        actual_a = clamp_acceleration(a, params.road_condition, v)
        
        dv = actual_a * dt_step
        v_new = v + dv
        
        if v_new < 0:
            v_new = 0.0
            actual_a = 0.0
        
        avg_v = (v + v_new) * 0.5
        dx = avg_v * dt_step
        
        x += dx * np.cos(theta)
        y += dx * np.sin(theta)
        
        v = v_new
    
    if pos_noise is not None:
        x += pos_noise[0]
        y += pos_noise[1]
    
    return x, y, v, actual_a


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
    
    x, y, v, actual_a = vehicle_position_at_time(
        params, t, 
        v_noise=noise['v_noise'],
        a_noise=noise['a_noise'],
        pos_noise=noise['pos_noise']
    )
    
    return VehicleState(
        x=x, y=y, v=v,
        a=actual_a,
        theta=np.radians(params.direction),
        length=params.length,
        width=params.width
    )


def get_road_display_name(condition_name: str) -> str:
    from .tire_model import get_road_condition
    road = get_road_condition(condition_name)
    return road.display_name


def list_road_conditions() -> list:
    from .tire_model import list_road_conditions
    return list_road_conditions()
