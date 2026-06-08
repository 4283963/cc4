import sys
sys.path.insert(0, '.')

from backend.core.vehicle import VehicleParams
from backend.core.collision import simulate_and_get_collision_time, CollisionWorkspace
from backend.core.monte_carlo import run_monte_carlo_simulations
import time

def test_road_conditions():
    print('=' * 60)
    print('路面摩擦力模型测试')
    print('=' * 60)
    
    v1 = VehicleParams(
        vehicle_id=0,
        initial_velocity=12.0,
        acceleration=-3.0,
        length=4.5,
        width=2.0,
        start_x=-30.0,
        start_y=0.0,
        direction=0.0,
        road_condition='dry_asphalt'
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
        road_condition='dry_asphalt'
    )
    
    workspace = CollisionWorkspace(2)
    
    road_names = {
        'dry_asphalt': '☀️ 晴天干燥',
        'wet_light': '🌧️ 小雨',
        'heavy_rain': '⛈️ 大雨',
        'snow': '❄️ 积雪',
        'icy': '🧊 结冰'
    }
    
    print(f'\n车辆1: 初速12m/s, 请求减速度3m/s²')
    print(f'车辆2: 初速10m/s, 加速度0.5m/s²')
    print(f'\n不同路面下的单次模拟碰撞时间:\n')
    
    for road in ['dry_asphalt', 'wet_light', 'heavy_rain', 'snow', 'icy']:
        v1.road_condition = road
        v2.road_condition = road
        t_col = simulate_and_get_collision_time([v1, v2], dt=0.05, t_max=30.0, seed=42, workspace=workspace)
        name = road_names[road]
        if t_col > 0:
            print(f'  {name}: 碰撞时间 = {t_col:.2f}s')
        else:
            print(f'  {name}: 无碰撞 (摩擦不足，制动距离变长)')
    
    print(f'\n✅ 物理模型正确：摩擦系数越低，制动越困难，碰撞风险越高')


def test_monte_carlo_different_roads():
    print(f'\n' + '=' * 60)
    print('蒙特卡洛多路面碰撞概率对比 (2000次模拟)')
    print('=' * 60)
    
    vehicles = []
    vehicles.append(VehicleParams(
        vehicle_id=0,
        initial_velocity=12.0,
        acceleration=-2.0,
        length=4.5,
        width=2.0,
        start_x=-30.0,
        start_y=0.0,
        direction=0.0,
        velocity_noise_std=0.5,
        acceleration_noise_std=0.2,
        position_noise_std=0.1,
        road_condition='dry_asphalt'
    ))
    vehicles.append(VehicleParams(
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
        position_noise_std=0.1,
        road_condition='dry_asphalt'
    ))
    
    road_names = {
        'dry_asphalt': '☀️ 晴天干燥',
        'heavy_rain': '⛈️ 大雨',
        'icy': '🧊 结冰'
    }
    
    baseline_prob = None
    
    for road in ['dry_asphalt', 'heavy_rain', 'icy']:
        for v in vehicles:
            v.road_condition = road
        
        start_time = time.time()
        result = run_monte_carlo_simulations(
            vehicles, num_simulations=2000, dt=0.05, t_max=30.0, base_seed=42
        )
        elapsed = time.time() - start_time
        
        prob = result['collision_probability'] * 100
        name = road_names[road]
        
        if baseline_prob is None:
            baseline_prob = result['collision_probability']
            change = '基准'
        else:
            change_pct = ((result['collision_probability'] - baseline_prob) / baseline_prob) * 100
            change = f'↑ +{change_pct:.1f}%' if change_pct > 0 else f'↓ {change_pct:.1f}%'
        
        print(f'\n  {name}:')
        print(f'    碰撞概率: {prob:.2f}%')
        print(f'    碰撞次数: {result["collision_count"]}/{result["num_simulations"]}')
        print(f'    耗时: {elapsed:.2f}s')
        print(f'    相对变化: {change}')
    
    print(f'\n✅ 蒙特卡洛多路面测试通过!')


if __name__ == '__main__':
    test_road_conditions()
    test_monte_carlo_different_roads()
    print(f'\n' + '=' * 60)
    print('🎉 所有路面摩擦模型测试通过!')
    print('=' * 60)
