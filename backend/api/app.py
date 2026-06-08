import uuid
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os

from ..core.vehicle import VehicleParams
from ..scheduler.parallel import ParallelScheduler
from ..cache.redis_cache import get_cache
from ..config import Config


def create_app():
    app = Flask(__name__, static_folder='../../frontend', static_url_path='')
    CORS(app)
    
    scheduler = ParallelScheduler()
    cache = get_cache()
    
    @app.route('/')
    def index():
        return send_from_directory('../../frontend', 'index.html')
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'ok',
            'redis_available': cache.redis_available,
            'num_processes': scheduler.num_processes
        })
    
    @app.route('/api/compute', methods=['POST'])
    def start_computation():
        data = request.get_json()
        
        if not data or 'vehicles' not in data:
            return jsonify({'error': 'Missing vehicles data'}), 400
        
        vehicles_data = data['vehicles']
        num_simulations = data.get('num_simulations', Config.MONTE_CARLO_SIMULATIONS)
        dt = data.get('dt', Config.TIME_STEP)
        t_max = data.get('t_max', Config.MAX_SIMULATION_TIME)
        base_seed = data.get('base_seed', 42)
        
        params_list = []
        for v_data in vehicles_data:
            params = VehicleParams(
                vehicle_id=v_data.get('id', len(params_list)),
                initial_velocity=v_data.get('initial_velocity', 10.0),
                acceleration=v_data.get('acceleration', 0.0),
                length=v_data.get('length', 4.5),
                width=v_data.get('width', 2.0),
                start_x=v_data.get('start_x', 0.0),
                start_y=v_data.get('start_y', 0.0),
                direction=v_data.get('direction', 0.0),
                velocity_noise_std=v_data.get('velocity_noise_std', 0.0),
                acceleration_noise_std=v_data.get('acceleration_noise_std', 0.0),
                position_noise_std=v_data.get('position_noise_std', 0.0)
            )
            params_list.append(params)
        
        params_dict = {
            'vehicles': [vars(p) for p in params_list],
            'num_simulations': num_simulations,
            'dt': dt,
            't_max': t_max,
            'base_seed': base_seed
        }
        
        cached_result = cache.get_cached_result(params_dict)
        if cached_result:
            return jsonify({
                'task_id': 'cached',
                'status': 'completed',
                'result': cached_result,
                'from_cache': True
            })
        
        task_id = str(uuid.uuid4())
        
        cache.set_task_status(task_id, 'queued', progress=0)
        
        from threading import Thread
        
        def run_task():
            cache.set_task_status(task_id, 'running', progress=0)
            
            def progress_callback(completed):
                progress = int((completed / num_simulations) * 100)
                cache.update_task_progress(task_id, progress)
            
            result = scheduler.run_parallel_monte_carlo(
                params_list,
                num_simulations=num_simulations,
                dt=dt,
                t_max=t_max,
                base_seed=base_seed,
                progress_callback=progress_callback
            )
            
            from ..core.monte_carlo import compute_confidence_interval
            p = result['collision_probability']
            ci_low, ci_high = compute_confidence_interval(p, num_simulations)
            result['confidence_interval_95_low'] = max(0.0, ci_low)
            result['confidence_interval_95_high'] = min(1.0, ci_high)
            
            if result.get('collision_times'):
                result['collision_times'] = result['collision_times'][:1000]
            
            cache.set_task_result(task_id, result)
            cache.cache_result(params_dict, result)
        
        thread = Thread(target=run_task, daemon=True)
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'status': 'queued',
            'from_cache': False
        })
    
    @app.route('/api/status/<task_id>', methods=['GET'])
    def get_status(task_id):
        status = cache.get_task_status(task_id)
        
        if status is None:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify(status)
    
    @app.route('/api/result/<task_id>', methods=['GET'])
    def get_result(task_id):
        status = cache.get_task_status(task_id)
        
        if status is None:
            return jsonify({'error': 'Task not found'}), 404
        
        if status['status'] != 'completed':
            return jsonify({
                'task_id': task_id,
                'status': status['status'],
                'progress': status.get('progress', 0)
            })
        
        return jsonify({
            'task_id': task_id,
            'status': 'completed',
            'result': status['result']
        })
    
    @app.route('/api/trajectory', methods=['POST'])
    def get_trajectory():
        data = request.get_json()
        
        if not data or 'vehicles' not in data:
            return jsonify({'error': 'Missing vehicles data'}), 400
        
        vehicles_data = data['vehicles']
        dt = data.get('dt', 0.05)
        t_max = data.get('t_max', Config.MAX_SIMULATION_TIME)
        add_noise = data.get('add_noise', False)
        seed = data.get('seed', 42)
        
        rng = np.random.default_rng(seed)
        
        trajectories = []
        for v_data in vehicles_data:
            params = VehicleParams(
                vehicle_id=v_data.get('id', 0),
                initial_velocity=v_data.get('initial_velocity', 10.0),
                acceleration=v_data.get('acceleration', 0.0),
                length=v_data.get('length', 4.5),
                width=v_data.get('width', 2.0),
                start_x=v_data.get('start_x', 0.0),
                start_y=v_data.get('start_y', 0.0),
                direction=v_data.get('direction', 0.0),
                velocity_noise_std=v_data.get('velocity_noise_std', 0.0),
                acceleration_noise_std=v_data.get('acceleration_noise_std', 0.0),
                position_noise_std=v_data.get('position_noise_std', 0.0)
            )
            
            noise = None
            if add_noise:
                from ..core.vehicle import generate_vehicle_noise
                noise = generate_vehicle_noise(params, rng)
            
            trajectory = []
            t = 0.0
            while t <= t_max:
                from ..core.vehicle import get_vehicle_state
                state = get_vehicle_state(params, t, noise)
                trajectory.append({
                    'time': round(t, 3),
                    'x': round(state.x, 4),
                    'y': round(state.y, 4),
                    'v': round(state.v, 4),
                    'theta': round(state.theta, 6),
                    'length': state.length,
                    'width': state.width
                })
                t += dt
            
            trajectories.append({
                'vehicle_id': params.vehicle_id,
                'trajectory': trajectory
            })
        
        return jsonify({
            'trajectories': trajectories,
            'dt': dt,
            't_max': t_max
        })
    
    @app.route('/api/intersection-info', methods=['GET'])
    def get_intersection_info():
        return jsonify({
            'width': Config.INTERSECTION_WIDTH,
            'height': Config.INTERSECTION_HEIGHT
        })
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=9000, debug=True)
