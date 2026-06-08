import numpy as np
from typing import List, Dict, Tuple, Callable
from .vehicle import VehicleParams
from .collision import simulate_trajectory_collision, get_collision_time


def run_monte_carlo_simulations(params_list: List[VehicleParams],
                                num_simulations: int,
                                dt: float = 0.01,
                                t_max: float = 30.0,
                                base_seed: int = 42,
                                progress_callback: Callable[[int], None] = None) -> Dict:
    collision_count = 0
    collision_times = []
    
    for i in range(num_simulations):
        seed = base_seed + i
        
        collision = simulate_trajectory_collision(
            params_list, dt=dt, t_max=t_max, seed=seed
        )
        
        if collision:
            collision_count += 1
            t_col = get_collision_time(params_list, dt=dt, t_max=t_max, seed=seed)
            if t_col > 0:
                collision_times.append(t_col)
        
        if progress_callback is not None and (i + 1) % max(1, num_simulations // 100) == 0:
            progress_callback(i + 1)
    
    collision_probability = collision_count / num_simulations
    
    result = {
        'num_simulations': num_simulations,
        'collision_count': collision_count,
        'collision_probability': collision_probability,
        'collision_times': collision_times if collision_times else [],
    }
    
    if collision_times:
        result['mean_collision_time'] = float(np.mean(collision_times))
        result['std_collision_time'] = float(np.std(collision_times))
        result['min_collision_time'] = float(np.min(collision_times))
        result['max_collision_time'] = float(np.max(collision_times))
    
    return result


def run_monte_carlo_batch(params_list: List[VehicleParams],
                          num_simulations: int,
                          dt: float,
                          t_max: float,
                          base_seed: int) -> Tuple[int, List[float]]:
    collision_count = 0
    collision_times = []
    
    for i in range(num_simulations):
        seed = base_seed + i
        collision = simulate_trajectory_collision(
            params_list, dt=dt, t_max=t_max, seed=seed
        )
        
        if collision:
            collision_count += 1
            t_col = get_collision_time(params_list, dt=dt, t_max=t_max, seed=seed)
            if t_col > 0:
                collision_times.append(t_col)
    
    return collision_count, collision_times


def compute_confidence_interval(p: float, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    from scipy import stats
    
    z = stats.norm.ppf((1 + confidence) / 2)
    margin = z * np.sqrt(p * (1 - p) / n)
    
    return p - margin, p + margin


def analyze_collision_risk(params_list: List[VehicleParams],
                           num_simulations: int = 100000,
                           dt: float = 0.01,
                           t_max: float = 30.0,
                           base_seed: int = 42) -> Dict:
    result = run_monte_carlo_simulations(
        params_list, num_simulations, dt, t_max, base_seed
    )
    
    p = result['collision_probability']
    ci_low, ci_high = compute_confidence_interval(p, num_simulations)
    
    result['confidence_interval_95_low'] = max(0.0, ci_low)
    result['confidence_interval_95_high'] = min(1.0, ci_high)
    result['coefficient_of_variation'] = (np.sqrt(p * (1 - p) / num_simulations) / p) if p > 0 else float('inf')
    
    return result
