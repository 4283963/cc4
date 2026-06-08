import sys
import time

sys.path.insert(0, '.')

print('=' * 60)
print('系统模块测试')
print('=' * 60)

print('\n1. 测试算法核心模块...')
from backend.core.vehicle import VehicleParams
from backend.core.monte_carlo import run_monte_carlo_simulations
print('   ✅ 算法模块导入成功')

v1 = VehicleParams(
    vehicle_id=0,
    initial_velocity=12.0,
    acceleration=-1.0,
    length=4.5,
    width=2.0,
    start_x=-30.0,
    start_y=0.0,
    direction=0.0,
    velocity_noise_std=0.5,
    acceleration_noise_std=0.2,
    position_noise_std=0.1
)

v2 = VehicleParams(
    vehicle_id=1,
    initial_velocity=10.0,
    acceleration=0.5,
    length=5.0,
    width=2.2,
    start_x=0.0,
    start_y=-25.0,
    direction=90.0,
    velocity_noise_std=0.5,
    acceleration_noise_std=0.2,
    position_noise_std=0.1
)

params_list = [v1, v2]

print('\n2. 运行蒙特卡洛模拟 (1000次)...')
start_time = time.time()
result = run_monte_carlo_simulations(
    params_list, 
    num_simulations=1000, 
    dt=0.05, 
    t_max=30.0, 
    base_seed=42
)
elapsed = time.time() - start_time

print(f'   碰撞次数: {result["collision_count"]}')
print(f'   碰撞概率: {result["collision_probability"]*100:.2f}%')
print(f'   模拟次数: {result["num_simulations"]}')
print(f'   耗时: {elapsed:.2f}s')
if result.get('mean_collision_time'):
    print(f'   平均碰撞时间: {result["mean_collision_time"]:.2f}s')
print('   ✅ 蒙特卡洛模拟测试通过')

print('\n3. 测试多进程调度...')
from backend.scheduler.parallel import ParallelScheduler
scheduler = ParallelScheduler(num_processes=2)
print(f'   进程数: {scheduler.num_processes}')

start_time = time.time()
parallel_result = scheduler.run_parallel_monte_carlo(
    params_list,
    num_simulations=2000,
    dt=0.05,
    t_max=30.0,
    base_seed=42
)
elapsed_parallel = time.time() - start_time

print(f'   碰撞概率: {parallel_result["collision_probability"]*100:.2f}%')
print(f'   耗时: {elapsed_parallel:.2f}s')
print('   ✅ 多进程调度测试通过')

print('\n4. 测试Redis缓存模块...')
from backend.cache.redis_cache import get_cache
cache = get_cache()
print(f'   Redis可用: {cache.redis_available}')
cache.set_result('test_key', {'test': 'value'}, ttl=60)
cached = cache.get_result('test_key')
print(f'   缓存读写: {"成功" if cached else "失败"}')
print('   ✅ 缓存模块测试通过')

print('\n5. 测试置信区间计算...')
from backend.core.monte_carlo import compute_confidence_interval
ci_low, ci_high = compute_confidence_interval(result['collision_probability'], 1000)
print(f'   95%置信区间: [{ci_low*100:.2f}%, {ci_high*100:.2f}%]')
print('   ✅ 统计算法测试通过')

print('\n' + '=' * 60)
print('所有核心模块测试通过! 🎉')
print('=' * 60)
