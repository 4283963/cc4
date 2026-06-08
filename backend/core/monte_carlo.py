import numpy as np
from typing import List, Dict, Tuple, Callable
from .vehicle import VehicleParams
from .collision import (
    simulate_and_get_collision_time,
    CollisionWorkspace,
    RunningStats
)
from ..config import Config


MAX_COLLISION_TIMES_SAMPLE = 1000


def run_monte_carlo_simulations(params_list: List[VehicleParams],
                                num_simulations: int,
                                dt: float = 0.01,
                                t_max: float = 30.0,
                                base_seed: int = 42,
                                progress_callback: Callable[[int], None] = None,
                                max_samples: int = MAX_COLLISION_TIMES_SAMPLE
                                ) -> Dict:
    num_vehicles = len(params_list)
    workspace = CollisionWorkspace(num_vehicles)
    
    collision_count = 0
    stats = RunningStats()
    
    collision_times_sample = np.zeros(max_samples, dtype=np.float64)
    sample_idx = 0
    sampling_rate = max(1, num_simulations // max_samples)
    
    progress_interval = max(1, num_simulations // 100)
    
    for i in range(num_simulations):
        seed = base_seed + i
        
        t_col = simulate_and_get_collision_time(
            params_list, dt=dt, t_max=t_max, seed=seed, workspace=workspace
        )
        
        if t_col >= 0:
            collision_count += 1
            stats.update(t_col)
            
            if sample_idx < max_samples and (i % sampling_rate == 0 or sample_idx < 100):
                collision_times_sample[sample_idx] = t_col
                sample_idx += 1
        
        if progress_callback is not None and (i + 1) % progress_interval == 0:
            progress_callback(i + 1)
    
    collision_probability = collision_count / num_simulations
    
    result = {
        'num_simulations': num_simulations,
        'collision_count': collision_count,
        'collision_probability': collision_probability,
        'collision_times_sample': collision_times_sample[:sample_idx].tolist(),
    }
    
    if stats.n > 0:
        result['mean_collision_time'] = float(stats.mean)
        result['std_collision_time'] = float(stats.std)
        result['min_collision_time'] = float(stats.min_val)
        result['max_collision_time'] = float(stats.max_val)
        result['collision_time_count'] = stats.n
    
    return result


def run_monte_carlo_batch(params_list: List[VehicleParams],
                          num_simulations: int,
                          dt: float,
                          t_max: float,
                          base_seed: int,
                          max_samples: int = MAX_COLLISION_TIMES_SAMPLE
                          ) -> Tuple[int, Dict]:
    num_vehicles = len(params_list)
    workspace = CollisionWorkspace(num_vehicles)
    
    collision_count = 0
    stats = RunningStats()
    
    sample_size = min(max_samples, num_simulations)
    collision_times_sample = np.zeros(sample_size, dtype=np.float64)
    sample_idx = 0
    sampling_rate = max(1, num_simulations // sample_size)
    
    for i in range(num_simulations):
        seed = base_seed + i
        
        t_col = simulate_and_get_collision_time(
            params_list, dt=dt, t_max=t_max, seed=seed, workspace=workspace
        )
        
        if t_col >= 0:
            collision_count += 1
            stats.update(t_col)
            
            if sample_idx < sample_size and (i % sampling_rate == 0 or sample_idx < 100):
                collision_times_sample[sample_idx] = t_col
                sample_idx += 1
    
    stats_dict = stats.to_dict()
    stats_dict['samples'] = collision_times_sample[:sample_idx].tolist()
    
    return collision_count, stats_dict


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


def merge_batch_stats(batch_stats_list: List[Dict]) -> Dict:
    total_n = 0
    total_mean = 0.0
    total_m2 = 0.0
    total_min = float('inf')
    total_max = float('-inf')
    all_samples = []
    
    for stats in batch_stats_list:
        if not stats or stats.get('count', 0) == 0:
            continue
        
        n = stats['count']
        mean = stats['mean']
        
        if n > 0:
            std = stats.get('std', 0.0)
            m2 = std * std * n
        else:
            m2 = 0.0
        
        if total_n == 0:
            total_n = n
            total_mean = mean
            total_m2 = m2
            total_min = stats['min']
            total_max = stats['max']
        else:
            delta = mean - total_mean
            total_mean += delta * n / (total_n + n)
            total_m2 += m2 + delta * delta * total_n * n / (total_n + n)
            total_n += n
            
            if stats['min'] < total_min:
                total_min = stats['min']
            if stats['max'] > total_max:
                total_max = stats['max']
        
        if 'samples' in stats:
            all_samples.extend(stats['samples'])
    
    if total_n == 0:
        return {}
    
    merged = {
        'count': total_n,
        'mean': total_mean,
        'std': np.sqrt(total_m2 / total_n),
        'min': total_min,
        'max': total_max,
        'samples': all_samples
    }
    
    return merged
