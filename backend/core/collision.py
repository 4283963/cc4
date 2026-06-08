import numpy as np
from typing import List, Tuple
from .vehicle import VehicleParams, VehicleState, get_vehicle_state, generate_vehicle_noise


def separating_axis_theorem(corners_a: np.ndarray, corners_b: np.ndarray) -> bool:
    polygons = [corners_a, corners_b]
    
    for polygon in polygons:
        for i in range(len(polygon)):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % len(polygon)]
            
            edge = p2 - p1
            normal = np.array([-edge[1], edge[0]])
            norm = np.linalg.norm(normal)
            if norm < 1e-10:
                continue
            normal = normal / norm
            
            min_a, max_a = project_polygon(corners_a, normal)
            min_b, max_b = project_polygon(corners_b, normal)
            
            if max_a < min_b or max_b < min_a:
                return False
    
    return True


def project_polygon(corners: np.ndarray, axis: np.ndarray) -> Tuple[float, float]:
    projections = corners @ axis
    return np.min(projections), np.max(projections)


def check_collision_between_states(state_a: VehicleState, state_b: VehicleState) -> bool:
    from .vehicle import get_vehicle_corners
    
    corners_a = get_vehicle_corners(state_a.x, state_a.y, state_a.theta, 
                                    state_a.length, state_a.width)
    corners_b = get_vehicle_corners(state_b.x, state_b.y, state_b.theta, 
                                    state_b.length, state_b.width)
    
    dx = abs(state_a.x - state_b.x)
    dy = abs(state_a.y - state_b.y)
    max_dim = max(state_a.length, state_a.width, state_b.length, state_b.width)
    if dx > max_dim or dy > max_dim:
        return False
    
    return separating_axis_theorem(corners_a, corners_b)


def check_collision_at_time(params_list: List[VehicleParams], t: float, 
                            noises: List[dict] = None) -> bool:
    if noises is None:
        noises = [{} for _ in params_list]
    
    states = [get_vehicle_state(params, t, noise) 
              for params, noise in zip(params_list, noises)]
    
    n = len(states)
    for i in range(n):
        for j in range(i + 1, n):
            if check_collision_between_states(states[i], states[j]):
                return True
    return False


def simulate_trajectory_collision(params_list: List[VehicleParams], 
                                  dt: float = 0.01, 
                                  t_max: float = 30.0,
                                  seed: int = None) -> bool:
    rng = np.random.default_rng(seed)
    
    noises = [generate_vehicle_noise(params, rng) for params in params_list]
    
    t = 0.0
    while t <= t_max:
        if check_collision_at_time(params_list, t, noises):
            return True
        t += dt
    
    return False


def get_collision_time(params_list: List[VehicleParams], 
                       dt: float = 0.01,
                       t_max: float = 30.0,
                       seed: int = None) -> float:
    rng = np.random.default_rng(seed)
    
    noises = [generate_vehicle_noise(params, rng) for params in params_list]
    
    t = 0.0
    while t <= t_max:
        if check_collision_at_time(params_list, t, noises):
            return t
        t += dt
    
    return -1.0


def get_vehicles_in_intersection(params_list: List[VehicleParams],
                                 intersection_width: float = 20.0,
                                 intersection_height: float = 20.0,
                                 dt: float = 0.01,
                                 t_max: float = 30.0,
                                 seed: int = None) -> List[Tuple[float, float]]:
    rng = np.random.default_rng(seed)
    noises = [generate_vehicle_noise(params, rng) for params in params_list]
    
    half_w = intersection_width / 2.0
    half_h = intersection_height / 2.0
    
    time_ranges = []
    
    for params, noise in zip(params_list, noises):
        t_enter = None
        t_leave = None
        
        t = 0.0
        while t <= t_max:
            state = get_vehicle_state(params, t, noise)
            in_x = -half_w <= state.x <= half_w
            in_y = -half_h <= state.y <= half_h
            
            if in_x and in_y:
                if t_enter is None:
                    t_enter = t
                t_leave = t
            elif t_enter is not None:
                break
            
            t += dt
        
        if t_enter is not None and t_leave is not None:
            time_ranges.append((t_enter, t_leave))
    
    return time_ranges
