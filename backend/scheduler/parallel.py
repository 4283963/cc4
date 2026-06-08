import numpy as np
import multiprocessing as mp
from typing import List, Dict, Callable, Optional
from ..core.vehicle import VehicleParams
from ..core.monte_carlo import run_monte_carlo_batch, merge_batch_stats
from ..config import Config


def _worker_func_pool(args):
    params_list_serializable, num_sims, dt, t_max, base_seed = args
    params_list = [VehicleParams(**p) for p in params_list_serializable]
    collision_count, stats_dict = run_monte_carlo_batch(
        params_list, num_sims, dt, t_max, base_seed
    )
    return collision_count, stats_dict


class ParallelScheduler:
    def __init__(self, num_processes: int = None):
        self.num_processes = num_processes or Config.NUM_PROCESSES
    
    def run_parallel_monte_carlo(self,
                                 params_list: List[VehicleParams],
                                 num_simulations: int = None,
                                 dt: float = None,
                                 t_max: float = None,
                                 base_seed: int = 42,
                                 progress_callback: Callable[[int], None] = None) -> Dict:
        
        num_simulations = num_simulations or Config.MONTE_CARLO_SIMULATIONS
        dt = dt or Config.TIME_STEP
        t_max = t_max or Config.MAX_SIMULATION_TIME
        
        params_serializable = [self._params_to_dict(p) for p in params_list]
        
        batch_size = num_simulations // self.num_processes
        remainder = num_simulations % self.num_processes
        
        tasks = []
        current_seed = base_seed
        for i in range(self.num_processes):
            sims_for_batch = batch_size + (1 if i < remainder else 0)
            if sims_for_batch > 0:
                tasks.append((
                    params_serializable,
                    sims_for_batch,
                    dt,
                    t_max,
                    current_seed
                ))
                current_seed += sims_for_batch
        
        total_collisions = 0
        batch_stats_list = []
        completed_sims = 0
        
        with mp.Pool(processes=self.num_processes) as pool:
            async_results = [pool.apply_async(_worker_func_pool, (task,)) for task in tasks]
            
            for async_result in async_results:
                collision_count, stats_dict = async_result.get()
                total_collisions += collision_count
                batch_stats_list.append(stats_dict)
                completed_sims += batch_size
                
                if progress_callback:
                    progress_callback(min(completed_sims, num_simulations))
        
        collision_probability = total_collisions / num_simulations
        
        merged_stats = merge_batch_stats(batch_stats_list)
        
        result = {
            'num_simulations': num_simulations,
            'collision_count': total_collisions,
            'collision_probability': collision_probability,
            'num_processes_used': self.num_processes
        }
        
        if merged_stats and merged_stats.get('count', 0) > 0:
            result['mean_collision_time'] = float(merged_stats['mean'])
            result['std_collision_time'] = float(merged_stats['std'])
            result['min_collision_time'] = float(merged_stats['min'])
            result['max_collision_time'] = float(merged_stats['max'])
            result['collision_time_count'] = merged_stats['count']
            result['collision_times_sample'] = merged_stats.get('samples', [])
        
        return result
    
    def _params_to_dict(self, params: VehicleParams) -> dict:
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
            'position_noise_std': params.position_noise_std,
            'road_condition': params.road_condition
        }


class AsyncComputeManager:
    def __init__(self, num_processes: int = None):
        self.scheduler = ParallelScheduler(num_processes)
        self._active_tasks = {}
    
    def start_computation(self, task_id: str, 
                          params_list: List[VehicleParams],
                          num_simulations: int = None,
                          dt: float = None,
                          t_max: float = None,
                          base_seed: int = 42) -> str:
        
        if task_id in self._active_tasks:
            return task_id
        
        from threading import Thread
        
        def run_computation():
            result = self.scheduler.run_parallel_monte_carlo(
                params_list, num_simulations, dt, t_max, base_seed
            )
            self._active_tasks[task_id] = {
                'status': 'completed',
                'result': result
            }
        
        self._active_tasks[task_id] = {
            'status': 'running',
            'result': None
        }
        
        thread = Thread(target=run_computation, daemon=True)
        thread.start()
        
        return task_id
    
    def get_status(self, task_id: str) -> Optional[dict]:
        return self._active_tasks.get(task_id)
    
    def get_result(self, task_id: str) -> Optional[dict]:
        task = self._active_tasks.get(task_id)
        if task and task['status'] == 'completed':
            return task['result']
        return None
