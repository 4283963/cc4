import numpy as np
from typing import List, Tuple, Optional
from .vehicle import VehicleParams, VehicleState, generate_vehicle_noise


class CollisionWorkspace:
    __slots__ = ('corners_a', 'corners_b', 'states', 'noises', 'rng',
                 'num_vehicles', '_corner_buf', '_proj_buf')
    
    def __init__(self, num_vehicles: int):
        self.num_vehicles = num_vehicles
        self.corners_a = np.zeros((4, 2), dtype=np.float64)
        self.corners_b = np.zeros((4, 2), dtype=np.float64)
        self.states = [None] * num_vehicles
        self.noises = [None] * num_vehicles
        self.rng = None
        self._corner_buf = np.zeros((4, 2), dtype=np.float64)
        self._proj_buf = np.zeros(4, dtype=np.float64)


def _get_vehicle_corners_inplace(x: float, y: float, theta: float,
                                 length: float, width: float,
                                 out: np.ndarray) -> None:
    half_l = length * 0.5
    half_w = width * 0.5
    
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    
    out[0, 0] = half_l * cos_t - half_w * sin_t + x
    out[0, 1] = half_l * sin_t + half_w * cos_t + y
    
    out[1, 0] = half_l * cos_t + half_w * sin_t + x
    out[1, 1] = half_l * sin_t - half_w * cos_t + y
    
    out[2, 0] = -half_l * cos_t + half_w * sin_t + x
    out[2, 1] = -half_l * sin_t - half_w * cos_t + y
    
    out[3, 0] = -half_l * cos_t - half_w * sin_t + x
    out[3, 1] = -half_l * sin_t + half_w * cos_t + y


def _separating_axis_theorem_inplace(corners_a: np.ndarray, 
                                     corners_b: np.ndarray,
                                     proj_buf: np.ndarray) -> bool:
    polygons = [corners_a, corners_b]
    
    for polygon in polygons:
        for i in range(4):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % 4]
            
            edge_x = p2[0] - p1[0]
            edge_y = p2[1] - p1[1]
            
            nx = -edge_y
            ny = edge_x
            
            norm = np.sqrt(nx * nx + ny * ny)
            if norm < 1e-10:
                continue
            
            nx /= norm
            ny /= norm
            
            proj_buf[0] = corners_a[0, 0] * nx + corners_a[0, 1] * ny
            proj_buf[1] = corners_a[1, 0] * nx + corners_a[1, 1] * ny
            proj_buf[2] = corners_a[2, 0] * nx + corners_a[2, 1] * ny
            proj_buf[3] = corners_a[3, 0] * nx + corners_a[3, 1] * ny
            min_a = proj_buf.min()
            max_a = proj_buf.max()
            
            proj_buf[0] = corners_b[0, 0] * nx + corners_b[0, 1] * ny
            proj_buf[1] = corners_b[1, 0] * nx + corners_b[1, 1] * ny
            proj_buf[2] = corners_b[2, 0] * nx + corners_b[2, 1] * ny
            proj_buf[3] = corners_b[3, 0] * nx + corners_b[3, 1] * ny
            min_b = proj_buf.min()
            max_b = proj_buf.max()
            
            if max_a < min_b or max_b < min_a:
                return False
    
    return True


def _check_collision_fast(params_list: List[VehicleParams], t: float,
                          noises: list, workspace: CollisionWorkspace) -> bool:
    num = len(params_list)
    
    for i in range(num):
        params = params_list[i]
        noise = noises[i]
        
        v0 = params.initial_velocity + noise['v_noise']
        a = params.acceleration + noise['a_noise']
        
        v = v0 + a * t
        if v < 0:
            v = 0.0
            a = 0.0
        
        dx = v0 * t + 0.5 * a * t * t
        theta = np.radians(params.direction)
        x = params.start_x + dx * np.cos(theta)
        y = params.start_y + dx * np.sin(theta)
        
        if noise['pos_noise'] is not None:
            x += noise['pos_noise'][0]
            y += noise['pos_noise'][1]
        
        state = workspace.states[i]
        if state is None:
            state = {'x': 0.0, 'y': 0.0, 'v': 0.0, 'theta': 0.0,
                     'length': params.length, 'width': params.width}
            workspace.states[i] = state
        
        state['x'] = x
        state['y'] = y
        state['v'] = v
        state['theta'] = theta
        state['length'] = params.length
        state['width'] = params.width
    
    for i in range(num):
        for j in range(i + 1, num):
            si = workspace.states[i]
            sj = workspace.states[j]
            
            dx = abs(si['x'] - sj['x'])
            dy = abs(si['y'] - sj['y'])
            max_dim = max(si['length'], si['width'], sj['length'], sj['width'])
            if dx > max_dim or dy > max_dim:
                continue
            
            _get_vehicle_corners_inplace(si['x'], si['y'], si['theta'],
                                         si['length'], si['width'],
                                         workspace.corners_a)
            _get_vehicle_corners_inplace(sj['x'], sj['y'], sj['theta'],
                                         sj['length'], sj['width'],
                                         workspace.corners_b)
            
            if _separating_axis_theorem_inplace(
                    workspace.corners_a, workspace.corners_b,
                    workspace._proj_buf):
                return True
    
    return False


def _init_noises(params_list: List[VehicleParams], rng, workspace: CollisionWorkspace):
    for i, params in enumerate(params_list):
        v_noise = rng.normal(0, params.velocity_noise_std) if params.velocity_noise_std > 0 else 0.0
        a_noise = rng.normal(0, params.acceleration_noise_std) if params.acceleration_noise_std > 0 else 0.0
        pos_noise = None
        if params.position_noise_std > 0:
            pos_noise = rng.normal(0, params.position_noise_std, size=2)
        workspace.noises[i] = {
            'v_noise': v_noise,
            'a_noise': a_noise,
            'pos_noise': pos_noise
        }


def simulate_and_get_collision_time(params_list: List[VehicleParams],
                                     dt: float = 0.01,
                                     t_max: float = 30.0,
                                     seed: int = None,
                                     workspace: CollisionWorkspace = None) -> float:
    if workspace is None:
        workspace = CollisionWorkspace(len(params_list))
    
    if workspace.rng is None:
        workspace.rng = np.random.default_rng(seed)
    else:
        workspace.rng = np.random.default_rng(seed)
    
    _init_noises(params_list, workspace.rng, workspace)
    
    t = 0.0
    while t <= t_max:
        if _check_collision_fast(params_list, t, workspace.noises, workspace):
            return t
        t += dt
    
    return -1.0


def simulate_trajectory_collision(params_list: List[VehicleParams],
                                  dt: float = 0.01,
                                  t_max: float = 30.0,
                                  seed: int = None,
                                  workspace: CollisionWorkspace = None) -> bool:
    return simulate_and_get_collision_time(
        params_list, dt, t_max, seed, workspace
    ) >= 0.0


def get_collision_time(params_list: List[VehicleParams],
                       dt: float = 0.01,
                       t_max: float = 30.0,
                       seed: int = None,
                       workspace: CollisionWorkspace = None) -> float:
    return simulate_and_get_collision_time(
        params_list, dt, t_max, seed, workspace
    )


def check_collision_at_time(params_list: List[VehicleParams], t: float,
                            noises: List[dict] = None) -> bool:
    if noises is None:
        noises = [{'v_noise': 0.0, 'a_noise': 0.0, 'pos_noise': None} 
                  for _ in params_list]
    
    workspace = CollisionWorkspace(len(params_list))
    for i in range(len(noises)):
        workspace.noises[i] = noises[i]
    
    return _check_collision_fast(params_list, t, workspace.noises, workspace)


def check_collision_between_states(state_a: dict, state_b: dict) -> bool:
    corners_a = np.zeros((4, 2), dtype=np.float64)
    corners_b = np.zeros((4, 2), dtype=np.float64)
    proj_buf = np.zeros(4, dtype=np.float64)
    
    _get_vehicle_corners_inplace(state_a.x, state_a.y, state_a.theta,
                                 state_a.length, state_a.width, corners_a)
    _get_vehicle_corners_inplace(state_b.x, state_b.y, state_b.theta,
                                 state_b.length, state_b.width, corners_b)
    
    return _separating_axis_theorem_inplace(corners_a, corners_b, proj_buf)


class RunningStats:
    __slots__ = ('n', 'mean', 'm2', 'min_val', 'max_val')
    
    def __init__(self):
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0
        self.min_val = float('inf')
        self.max_val = float('-inf')
    
    def update(self, value: float):
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        delta2 = value - self.mean
        self.m2 += delta * delta2
        
        if value < self.min_val:
            self.min_val = value
        if value > self.max_val:
            self.max_val = value
    
    @property
    def variance(self) -> float:
        return self.m2 / self.n if self.n > 0 else 0.0
    
    @property
    def std(self) -> float:
        return np.sqrt(self.variance)
    
    def to_dict(self) -> dict:
        if self.n == 0:
            return {}
        return {
            'count': self.n,
            'mean': self.mean,
            'std': self.std,
            'min': self.min_val,
            'max': self.max_val
        }
