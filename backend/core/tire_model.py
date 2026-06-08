import numpy as np
from dataclasses import dataclass
from typing import Dict


@dataclass
class RoadCondition:
    name: str
    display_name: str
    peak_friction_coeff: float
    shape_factor_C: float
    stiffness_factor_B: float
    curvature_factor_E: float
    description: str


ROAD_CONDITIONS: Dict[str, RoadCondition] = {
    'dry_asphalt': RoadCondition(
        name='dry_asphalt',
        display_name='晴天干燥路面',
        peak_friction_coeff=0.85,
        shape_factor_C=1.3,
        stiffness_factor_B=10.0,
        curvature_factor_E=0.97,
        description='干燥沥青路面，轮胎抓地力最佳'
    ),
    'wet_light': RoadCondition(
        name='wet_light',
        display_name='小雨路面',
        peak_friction_coeff=0.65,
        shape_factor_C=1.25,
        stiffness_factor_B=9.0,
        curvature_factor_E=0.95,
        description='小雨路面，摩擦系数略有下降'
    ),
    'heavy_rain': RoadCondition(
        name='heavy_rain',
        display_name='大雨路面',
        peak_friction_coeff=0.45,
        shape_factor_C=1.2,
        stiffness_factor_B=7.5,
        curvature_factor_E=0.9,
        description='大雨路面，水滑效应明显，制动距离增加'
    ),
    'icy': RoadCondition(
        name='icy',
        display_name='结冰路面',
        peak_friction_coeff=0.15,
        shape_factor_C=1.1,
        stiffness_factor_B=5.0,
        curvature_factor_E=0.8,
        description='结冰路面，摩擦系数极低，极易侧滑'
    ),
    'snow': RoadCondition(
        name='snow',
        display_name='积雪路面',
        peak_friction_coeff=0.25,
        shape_factor_C=1.15,
        stiffness_factor_B=6.0,
        curvature_factor_E=0.85,
        description='积雪路面，摩擦系数较低，车辆易打滑'
    )
}


def magic_formula_longitudinal_force(slip_ratio: float,
                                  peak_friction: float,
                                  C: float,
                                  B: float,
                                  E: float,
                                  normal_force: float = 1.0) -> float:
    slip_angle = np.radians(slip_ratio * 30.0)
    
    Bx = B * slip_angle
    Fx = D * np.sin(C * np.arctan(Bx - E * (Bx - np.arctan(Bx))))
    
    return Fx * normal_force


def magic_formula_lateral(slip_angle_deg: float,
                         road: RoadCondition,
                         normal_force: float = 1.0) -> float:
    D = road.peak_friction_coeff
    C = road.shape_factor_C
    B = road.stiffness_factor_B
    E = road.curvature_factor_E
    
    alpha = np.radians(slip_angle_deg)
    
    B_alpha = B * alpha
    F_y = D * np.sin(C * np.arctan(B_alpha - E * (B_alpha - np.arctan(B_alpha))))
    
    return F_y * normal_force


def magic_formula_longitudinal(slip_ratio: float,
                               road: RoadCondition,
                               normal_force: float = 1.0) -> float:
    D = road.peak_friction_coeff
    C = road.shape_factor_C
    B = road.stiffness_factor_B
    E = road.curvature_factor_E
    
    B_kappa = B * slip_ratio * 10.0
    F_x = D * np.sin(C * np.arctan(B_kappa - E * (B_kappa - np.arctan(B_kappa))))
    
    return F_x * normal_force


def combined_slip_force(slip_ratio: float,
                      slip_angle_deg: float,
                      road: RoadCondition,
                      normal_force: float = 1.0) -> tuple:
    Fx = magic_formula_longitudinal(slip_ratio, road, normal_force)
    Fy = magic_formula_lateral(slip_angle_deg, road, normal_force)
    
    rho = np.sqrt(Fx * Fx + Fy * Fy)
    F_max = road.peak_friction_coeff * normal_force
    
    if rho > F_max * 0.95:
        scale = F_max * 0.95 / rho
        Fx *= scale
        Fy *= scale
    
    return Fx, Fy


def max_braking_acceleration(road: RoadCondition,
                              velocity: float,
                              is_braking: bool = True) -> float:
    mu = road.peak_friction_coeff
    
    v_norm = min(1.0)
    
    if velocity > 0:
        pass
    
    return mu * 9.81 * v_norm


def compute_effective_friction(velocity: float, road: RoadCondition) -> float:
    mu_peak = road.peak_friction_coeff
    v_ref = 20.0
    decay_rate = 0.01
    
    if velocity > v_ref:
        factor = 1.0 - decay_rate * (velocity - v_ref)
        factor = max(0.5, factor)
    else:
        factor = 1.0
    
    return mu_peak * factor


def get_road_condition(condition_name: str) -> RoadCondition:
    return ROAD_CONDITIONS.get(condition_name, ROAD_CONDITIONS['dry_asphalt'])


def list_road_conditions() -> list:
    return [
        {
            'name': rc.name,
            'display_name': rc.display_name,
            'peak_friction_coeff': rc.peak_friction_coeff,
            'description': rc.description
        }
        for rc in ROAD_CONDITIONS.values()
    ]
