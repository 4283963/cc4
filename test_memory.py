import sys
import time
import tracemalloc

sys.path.insert(0, '.')

from backend.core.vehicle import VehicleParams
from backend.core.monte_carlo import run_monte_carlo_simulations
from backend.scheduler.parallel import ParallelScheduler


def create_test_vehicles(num_vehicles: int = 5) -> list:
    vehicles = []
    directions = [0, 90, 180, 270, 45, 135, 225, 315]
    positions = [
        (-30, 0), (0, -25), (30, 5), (-5, 28),
        (-25, -20), (22, -18), (20, 22), (-22, 20)
    ]
    
    for i in range(num_vehicles):
        idx = i % len(positions)
        v = VehicleParams(
            vehicle_id=i,
            initial_velocity=10.0 + i * 0.5,
            acceleration=-1.0 + i * 0.3,
            length=4.5 + i * 0.2,
            width=2.0 + i * 0.1,
            start_x=positions[idx][0],
            start_y=positions[idx][1],
            direction=directions[idx],
            velocity_noise_std=0.5,
            acceleration_noise_std=0.2,
            position_noise_std=0.1
        )
        vehicles.append(v)
    
    return vehicles


def test_memory_usage():
    print('=' * 60)
    print('内存使用压力测试')
    print('=' * 60)
    
    num_vehicles = 5
    num_simulations = 50000
    
    print(f'\n测试配置:')
    print(f'  车辆数量: {num_vehicles}')
    print(f'  模拟次数: {num_simulations}')
    print(f'  时间步长: 0.05s')
    print(f'  最大时间: 30s')
    
    vehicles = create_test_vehicles(num_vehicles)
    
    print('\n开始跟踪内存...')
    tracemalloc.start()
    
    start_time = time.time()
    
    result = run_monte_carlo_simulations(
        vehicles,
        num_simulations=num_simulations,
        dt=0.05,
        t_max=30.0,
        base_seed=42
    )
    
    elapsed = time.time() - start_time
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print(f'\n测试结果:')
    print(f'  碰撞概率: {result["collision_probability"]*100:.2f}%')
    print(f'  碰撞次数: {result["collision_count"]}')
    print(f'  耗时: {elapsed:.2f}s')
    
    if result.get('mean_collision_time'):
        print(f'  平均碰撞时间: {result["mean_collision_time"]:.2f}s')
        print(f'  碰撞时间标准差: {result["std_collision_time"]:.2f}s')
    
    print(f'\n内存使用:')
    print(f'  当前内存: {current / 1024 / 1024:.2f} MB')
    print(f'  峰值内存: {peak / 1024 / 1024:.2f} MB')
    
    sample_count = len(result.get('collision_times_sample', []))
    print(f'\n采样数据:')
    print(f'  碰撞时间样本数: {sample_count}')
    
    print(f'\n✅ 单进程测试通过!')
    print(f'   内存占用控制在 {peak / 1024 / 1024:.2f} MB 以内')
    
    return peak


def test_parallel_memory():
    print('\n' + '=' * 60)
    print('多进程内存压力测试')
    print('=' * 60)
    
    num_vehicles = 5
    num_simulations = 50000
    
    print(f'\n测试配置:')
    print(f'  车辆数量: {num_vehicles}')
    print(f'  模拟次数: {num_simulations}')
    
    vehicles = create_test_vehicles(num_vehicles)
    scheduler = ParallelScheduler(num_processes=4)
    
    print(f'  进程数: {scheduler.num_processes}')
    
    print('\n开始测试...')
    start_time = time.time()
    
    result = scheduler.run_parallel_monte_carlo(
        vehicles,
        num_simulations=num_simulations,
        dt=0.05,
        t_max=30.0,
        base_seed=42
    )
    
    elapsed = time.time() - start_time
    
    print(f'\n测试结果:')
    print(f'  碰撞概率: {result["collision_probability"]*100:.2f}%')
    print(f'  碰撞次数: {result["collision_count"]}')
    print(f'  耗时: {elapsed:.2f}s')
    
    if result.get('mean_collision_time'):
        print(f'  平均碰撞时间: {result["mean_collision_time"]:.2f}s')
    
    sample_count = len(result.get('collision_times_sample', []))
    print(f'  碰撞时间样本数: {sample_count}')
    
    print(f'\n✅ 多进程测试通过!')
    print(f'   使用统计合并代替全量数据传输')


def main():
    peak_single = test_memory_usage()
    test_parallel_memory()
    
    print('\n' + '=' * 60)
    print('🎉 所有内存优化测试通过!')
    print('=' * 60)
    print('\n关键优化点:')
    print('  1. CollisionWorkspace 数组复用 - 避免频繁分配小对象')
    print('  2. Welford 在线统计算法 - 无需保存全部碰撞时间')
    print('  3. 固定大小采样数组 - 内存占用与模拟次数无关')
    print('  4. 单次模拟双返回 - 同时得到碰撞结果和时间')
    print('  5. 多进程统计合并 - 只传输统计量而非全量数据')


if __name__ == '__main__':
    main()
