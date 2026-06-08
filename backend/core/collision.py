import numpy as np
from typing import List, Tuple, Optional
from .vehicle import VehicleParams, VehicleState, generate_vehicle_noise


class VehicleSimState:
    __slots__ = ('x', 'y', 'v', 'a_requested', 'a_effective', 'theta',
                 'length', 'width', 'road_condition', 'v0_noise', 'a_noise',
                 'pos_noise')
    
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.v = 0.0
        self.a_requested = 0.0
        self.a_effective = 0.0
        self.theta = 0.0
        self.length = 0.0
        self.width = 0.0
        self.road_condition = 'dry_asphalt'
        self.v0_noise = 0.0
        self.a_noise = 0.0
        self.pos_noise = None
    
    def reset(self, params: VehicleParams, noise: dict):
        self.x = params.start_x
        self.y = params.start_y
        self.v = params.initial_velocity + noise['v_noise']
        self.a_requested = params.acceleration + noise['a_noise']
        self.theta = np.radians(params.direction)
        self.length = params.length
        self.width = params.width
        self.road_condition = params.road_condition
        self.v0_noise = noise['v_noise']
        self.a_noise = noise['a_noise']
        self.pos_noise = noise['pos_noise']
    
    def step(self, dt: float):
        mu = self._get_friction(self.v)
        max_brake = -mu * 9.81
        max_drive = mu * 9.81 * 0.6
        
        if self.a_requested < max_brake:
            self.a_effective = max_brake
        elif self.a_requested > max_drive:
            self.a_effective = max_drive
        else:
            self.a_effective = self.a_requested
        
        dv = self.a_effective * dt
        v_new = self.v + dv
        
        if v_new < 0:
            v_new = 0.0
            self.a_effective = 0.0
        
        avg_v = (self.v + v_new) * 0.5
        dx = avg_v * dt
        
        self.x += dx * np.cos(self.theta)
        self.y += dx * np.sin(self.theta)
        self.v = v_new
    
    def _get_friction(self, velocity: float) -> float:
        road_mu = {
            'dry_asphalt': 0.85,
            'wet_light': 0.65,
            'heavy_rain': 0.45,
            'icy': 0.15,
            'snow': 0.25
        }
        mu_peak = road_mu.get(self.road_condition, 0.85)
        
        v_ref = 20.0
        if velocity > v_ref:
            decay = 0.01 * (velocity - v_ref)
            decay = min(decay, 0.5)
            mu = mu_peak * (1.0 - decay)
        else:
            mu = mu_peak
        
        return mu
    
    def get_position(self) -> Tuple[float, float]:
        if self.pos_noise is not None:
            return self.x + self.pos_noise[0], self.y + self.pos_noise[1]
        return self.x, self.y


class CollisionWorkspace:
    __slots__ = ('corners_a', 'corners_b', 'vehicle_states', 'noises', 'rng',
                 'num_vehicles', '_corner_buf', '_proj_buf',
                 '_current_time', '_sim_dt', '_params_list_ref')
    
    def __init__(self, num_vehicles: int):
        self.num_vehicles = num_vehicles
        self.corners_a = np.zeros((4, 2), dtype=np.float64)
        self.corners_b = np.zeros((4, 2), dtype=np.float64)
        self.vehicle_states = [VehicleSimState() for _ in range(num_vehicles)]
        self.noises = [None] * num_vehicles
        self.rng = None
        self._corner_buf = np.zeros((4, 2), dtype=np.float64)
        self._proj_buf = np.zeros(4, dtype=np.float64)
        self._current_time = 0.0
        self._sim_dt = 0.01
        self._params_list_ref = None
    
    def init_simulation(self, params_list: List[VehicleParams], 
                        dt: float, seed: int):
        self._params_list_ref = params_list
        self._sim_dt = dt
        self._current_time = 0.0
        
        if self.rng is None:
            self.rng = np.random.default_rng(seed)
        else:
            self.rng.bit_generator.state = np.random.default_rng(seed).bit_generator.state
        
        for i, params in enumerate(params_list):
            noise = self._gen_noise(params)
            self.noises[i] = noise
            self.vehicle_states[i].reset(params, noise)
    
    def _gen_noise(self, params: VehicleParams) -> dict:
        v_noise = self.rng.normal(0, params.velocity_noise_std) if params.velocity_noise_std > 0 else 0.0
        a_noise = self.rng.normal(0, params.acceleration_noise_std) if params.acceleration_noise_std > 0 else 0.0
        pos_noise = None
        if params.position_noise_std > 0:
            pos_noise = self.rng.normal(0, params.position_noise_std, size=2)
        return {
            'v_noise': v_noise,
            'a_noise': a_noise,
            'pos_noise': pos_noise
        }
    
    def advance_to_time(self, target_time: float):
        if target_time <= self._current_time:
            return
        
        while self._current_time + self._sim_dt <= target_time:
            for i in range(self.num_vehicles):
                self.vehicle_states[i].step(self._sim_dt)
            self._current_time += self._sim_dt
        
        remainder = target_time - self._current_time
        if remainder > 1e-10:
            for i in range(self.num_vehicles):
                self.vehicle_states[i].step(remainder)
            self._current_time = target_time


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


def _check_collision_in_workspace(workspace: CollisionWorkspace) -> bool:
    num = workspace.num_vehicles
    
    for i in range(num):
        for j in range(i + 1, num):
            si = workspace.vehicle_states[i]
            sj = workspace.vehicle_states[j]
            
            dx = abs(si.x - sj.x)
            dy = abs(si.y - sj.y)
            max_dim = max(si.length, si.width, sj.length, sj.width)
            if dx > max_dim or dy > max_dim:
                continue
            
            x_i, y_i = si.get_position()
            x_j, y_j = sj.get_position()
            
            _get_vehicle_corners_inplace(x_i, y_i, si.theta,
                                         si.length, si.width,
                                         workspace.corners_a)
            _get_vehicle_corners_inplace(x_j, y_j, sj.theta,
                                         sj.length, sj.width,
                                         workspace.corners_b)
            
            if _separating_axis_theorem_inplace(
                    workspace.corners_a, workspace.corners_b,
                    workspace._proj_buf):
                return True
    
    return False


def simulate_and_get_collision_time(params_list: List[VehicleParams],
                                     dt: float = 0.01,
                                     t_max: float = 30.0,
                                     seed: int = None,
                                     workspace: CollisionWorkspace = None) -> float:
    if workspace is None:
        workspace = CollisionWorkspace(len(params_list))
    
    workspace.init_simulation(params_list, dt, seed)
    
    t = 0.0
    while t <= t_max:
        workspace.advance_to_time(t)
        
        if _check_collision_in_workspace(workspace):
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
    for i in range(len(params_list)):
        workspace.noises[i] = noises[i]
        workspace.vehicle_states[i].reset(params_list[i], noises[i])
    
    workspace._current_time = 0.0
    workspace._sim_dt = min(0.01, t / 100.0)
    
    workspace.advance_to_time(t)
    return _check_collision_in_workspace(workspace)


def check_collision_between_states(state_a: VehicleState, state_b: VehicleState) -> bool:
    corners_a = np.zeros((4, 2), dtype=np.float64)
    corners_b = np.zeros((4, 2), dtype=np.float64)
    proj_buf = np.zeros(4, dtype=np.float64)
    
    from .vehicle import get_vehicle_corners
    ca = get_vehicle_corners(state_a.x, state_a.y, state_a.theta,
                             state_a.length, state_a.width)
    cb = get_vehicle_corners(state_b.x, state_b.y, state_b.theta,
                             state_b.length, state_b.width)
    
    return _separating_axis_theorem_inplace(ca, cb, proj_buf)


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
