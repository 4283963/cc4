import os

class Config:
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    
    MONTE_CARLO_SIMULATIONS = 100000
    
    NUM_PROCESSES = os.cpu_count() or 4
    
    TIME_STEP = 0.01
    MAX_SIMULATION_TIME = 30.0
    
    INTERSECTION_WIDTH = 20.0
    INTERSECTION_HEIGHT = 20.0
    
    CACHE_TTL = 3600
