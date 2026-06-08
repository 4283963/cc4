class CollisionSimulationApp {
    constructor() {
        this.canvas = document.getElementById('simulationCanvas');
        this.ctx = this.canvas.getContext('2d');
        
        this.vehicles = [];
        this.trajectories = [];
        this.currentTime = 0;
        this.isPlaying = false;
        this.animationId = null;
        this.dt = 0.033;
        
        this.scale = 8;
        this.offsetX = this.canvas.width / 2;
        this.offsetY = this.canvas.height / 2;
        
        this.intersectionWidth = 20;
        this.intersectionHeight = 20;
        
        this.currentTaskId = null;
        this.pollingInterval = null;
        this.compareTaskId = null;
        this.comparePollingInterval = null;
        
        this.editingVehicleIndex = -1;
        
        this.vehicleColors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c'];
        
        this.roadCondition = 'dry_asphalt';
        this.roadConditions = {
            'dry_asphalt': { name: '晴天干燥路面', icon: '☀️', mu: 0.85, desc: '干燥沥青路面，轮胎抓地力最佳' },
            'wet_light': { name: '小雨路面', icon: '🌧️', mu: 0.65, desc: '小雨路面，摩擦系数略有下降' },
            'heavy_rain': { name: '大雨路面', icon: '⛈️', mu: 0.45, desc: '大雨路面，水滑效应明显，制动距离增加' },
            'snow': { name: '积雪路面', icon: '❄️', mu: 0.25, desc: '积雪路面，摩擦系数较低，车辆易打滑' },
            'icy': { name: '结冰路面', icon: '🧊', mu: 0.15, desc: '结冰路面，摩擦系数极低，极易侧滑' }
        };
        
        this.compareConditions = ['dry_asphalt', 'wet_light', 'heavy_rain', 'icy'];
        
        this.init();
    }
    
    init() {
        this.setupCanvas();
        this.bindEvents();
        this.addDefaultVehicles();
        this.checkSystemStatus();
        this.fetchTrajectory();
        this.animate();
    }
    
    setupCanvas() {
        const container = this.canvas.parentElement;
        const rect = container.getBoundingClientRect();
        const size = Math.min(rect.width - 40, 600);
        this.canvas.width = size;
        this.canvas.height = size;
        this.offsetX = this.canvas.width / 2;
        this.offsetY = this.canvas.height / 2;
        this.scale = size / 80;
    }
    
    bindEvents() {
        document.getElementById('playBtn').addEventListener('click', () => this.play());
        document.getElementById('pauseBtn').addEventListener('click', () => this.pause());
        document.getElementById('resetBtn').addEventListener('click', () => this.reset());
        
        document.getElementById('addVehicleBtn').addEventListener('click', () => this.openAddVehicleModal());
        document.getElementById('computeBtn').addEventListener('click', () => this.startComputation());
        document.getElementById('compareBtn').addEventListener('click', () => this.startComparison());
        
        document.getElementById('roadCondition').addEventListener('change', (e) => {
            this.roadCondition = e.target.value;
            this.updateRoadDescription();
            this.fetchTrajectory();
        });
        
        document.getElementById('closeModal').addEventListener('click', () => this.closeModal());
        document.getElementById('cancelVehicle').addEventListener('click', () => this.closeModal());
        document.getElementById('saveVehicle').addEventListener('click', () => this.saveVehicle());
        
        document.getElementById('vehicleModal').addEventListener('click', (e) => {
            if (e.target.id === 'vehicleModal') {
                this.closeModal();
            }
        });
        
        window.addEventListener('resize', () => this.setupCanvas());
    }
    
    addDefaultVehicles() {
        this.vehicles = [
            {
                id: 0,
                initial_velocity: 12.0,
                acceleration: -1.0,
                length: 4.5,
                width: 2.0,
                start_x: -30.0,
                start_y: 0.0,
                direction: 0.0,
                velocity_noise_std: 0.5,
                acceleration_noise_std: 0.2,
                position_noise_std: 0.1,
                color: '#3498db'
            },
            {
                id: 1,
                initial_velocity: 10.0,
                acceleration: 0.5,
                length: 5.0,
                width: 2.2,
                start_x: 0.0,
                start_y: -25.0,
                direction: 90.0,
                velocity_noise_std: 0.5,
                acceleration_noise_std: 0.2,
                position_noise_std: 0.1,
                color: '#e74c3c'
            }
        ];
        this.renderVehicleList();
    }
    
    renderVehicleList() {
        const list = document.getElementById('vehicleList');
        list.innerHTML = '';
        
        this.vehicles.forEach((v, index) => {
            const item = document.createElement('div');
            item.className = 'vehicle-item';
            item.innerHTML = `
                <div class="vehicle-color" style="background: ${v.color}"></div>
                <div class="vehicle-info">
                    <div class="name">车辆 ${index + 1}</div>
                    <div class="desc">v₀=${v.initial_velocity}m/s | a=${v.acceleration}m/s² | 方向=${v.direction}°</div>
                </div>
                <button class="vehicle-delete" data-index="${index}">×</button>
            `;
            
            item.addEventListener('click', (e) => {
                if (!e.target.classList.contains('vehicle-delete')) {
                    this.openEditVehicleModal(index);
                }
            });
            
            item.querySelector('.vehicle-delete').addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteVehicle(index);
            });
            
            list.appendChild(item);
        });
    }
    
    openAddVehicleModal() {
        this.editingVehicleIndex = -1;
        document.getElementById('modalTitle').textContent = '添加车辆';
        
        const newIndex = this.vehicles.length;
        document.getElementById('vInitialVelocity').value = 10;
        document.getElementById('vAcceleration').value = 0;
        document.getElementById('vLength').value = 4.5;
        document.getElementById('vWidth').value = 2.0;
        document.getElementById('vStartX').value = -30;
        document.getElementById('vStartY').value = (newIndex - 1) * 5;
        document.getElementById('vDirection').value = 0;
        document.getElementById('vVelNoise').value = 0.5;
        document.getElementById('vAccNoise').value = 0.2;
        document.getElementById('vPosNoise').value = 0.1;
        document.getElementById('vColor').value = this.vehicleColors[newIndex % this.vehicleColors.length];
        
        document.getElementById('vehicleModal').style.display = 'flex';
    }
    
    openEditVehicleModal(index) {
        this.editingVehicleIndex = index;
        document.getElementById('modalTitle').textContent = '编辑车辆参数';
        
        const v = this.vehicles[index];
        document.getElementById('vInitialVelocity').value = v.initial_velocity;
        document.getElementById('vAcceleration').value = v.acceleration;
        document.getElementById('vLength').value = v.length;
        document.getElementById('vWidth').value = v.width;
        document.getElementById('vStartX').value = v.start_x;
        document.getElementById('vStartY').value = v.start_y;
        document.getElementById('vDirection').value = v.direction;
        document.getElementById('vVelNoise').value = v.velocity_noise_std;
        document.getElementById('vAccNoise').value = v.acceleration_noise_std;
        document.getElementById('vPosNoise').value = v.position_noise_std;
        document.getElementById('vColor').value = v.color;
        
        document.getElementById('vehicleModal').style.display = 'flex';
    }
    
    closeModal() {
        document.getElementById('vehicleModal').style.display = 'none';
    }
    
    saveVehicle() {
        const vehicleData = {
            id: this.editingVehicleIndex >= 0 ? this.vehicles[this.editingVehicleIndex].id : this.vehicles.length,
            initial_velocity: parseFloat(document.getElementById('vInitialVelocity').value) || 0,
            acceleration: parseFloat(document.getElementById('vAcceleration').value) || 0,
            length: parseFloat(document.getElementById('vLength').value) || 4.5,
            width: parseFloat(document.getElementById('vWidth').value) || 2.0,
            start_x: parseFloat(document.getElementById('vStartX').value) || 0,
            start_y: parseFloat(document.getElementById('vStartY').value) || 0,
            direction: parseFloat(document.getElementById('vDirection').value) || 0,
            velocity_noise_std: parseFloat(document.getElementById('vVelNoise').value) || 0,
            acceleration_noise_std: parseFloat(document.getElementById('vAccNoise').value) || 0,
            position_noise_std: parseFloat(document.getElementById('vPosNoise').value) || 0,
            color: document.getElementById('vColor').value
        };
        
        if (this.editingVehicleIndex >= 0) {
            this.vehicles[this.editingVehicleIndex] = vehicleData;
        } else {
            this.vehicles.push(vehicleData);
        }
        
        this.renderVehicleList();
        this.fetchTrajectory();
        this.closeModal();
    }
    
    deleteVehicle(index) {
        if (this.vehicles.length <= 1) {
            alert('至少需要保留一辆车');
            return;
        }
        this.vehicles.splice(index, 1);
        this.renderVehicleList();
        this.fetchTrajectory();
    }
    
    async fetchTrajectory() {
        if (this.vehicles.length === 0) return;
        
        try {
            const response = await fetch('/api/trajectory', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vehicles: this.vehicles,
                    road_condition: this.roadCondition,
                    dt: 0.05,
                    t_max: 30,
                    add_noise: false,
                    seed: 42
                })
            });
            
            const data = await response.json();
            this.trajectories = data.trajectories;
            this.currentTime = 0;
        } catch (err) {
            console.error('获取轨迹失败:', err);
        }
    }
    
    updateRoadDescription() {
        const road = this.roadConditions[this.roadCondition];
        if (road) {
            document.getElementById('roadDesc').textContent = road.desc;
        }
    }
    
    play() {
        this.isPlaying = true;
    }
    
    pause() {
        this.isPlaying = false;
    }
    
    reset() {
        this.isPlaying = false;
        this.currentTime = 0;
    }
    
    animate() {
        if (this.isPlaying) {
            this.currentTime += this.dt;
            if (this.currentTime > 30) {
                this.currentTime = 0;
            }
        }
        
        document.getElementById('timeDisplay').textContent = this.currentTime.toFixed(2);
        
        this.draw();
        this.animationId = requestAnimationFrame(() => this.animate());
    }
    
    draw() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;
        
        ctx.clearRect(0, 0, w, h);
        
        this.drawIntersection();
        this.drawTrajectories();
        this.drawVehicles();
    }
    
    drawIntersection() {
        const ctx = this.ctx;
        const halfW = this.intersectionWidth / 2;
        const halfH = this.intersectionHeight / 2;
        
        ctx.fillStyle = '#2a2a3a';
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        ctx.fillStyle = '#3a3a4a';
        ctx.fillRect(0, this.offsetY - halfH * this.scale, 
                     this.canvas.width, this.intersectionHeight * this.scale);
        ctx.fillRect(this.offsetX - halfW * this.scale, 0,
                     this.intersectionWidth * this.scale, this.canvas.height);
        
        ctx.strokeStyle = '#ffd93d';
        ctx.lineWidth = 2;
        ctx.setLineDash([10, 10]);
        
        ctx.beginPath();
        ctx.moveTo(0, this.offsetY);
        ctx.lineTo(this.canvas.width, this.offsetY);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(this.offsetX, 0);
        ctx.lineTo(this.offsetX, this.canvas.height);
        ctx.stroke();
        
        ctx.setLineDash([]);
        
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1;
        ctx.strokeRect(
            this.offsetX - halfW * this.scale,
            this.offsetY - halfH * this.scale,
            this.intersectionWidth * this.scale,
            this.intersectionHeight * this.scale
        );
    }
    
    drawTrajectories() {
        const ctx = this.ctx;
        
        this.trajectories.forEach((traj, index) => {
            const color = this.vehicles[index]?.color || '#3498db';
            
            ctx.strokeStyle = color + '40';
            ctx.lineWidth = 2;
            ctx.beginPath();
            
            traj.trajectory.forEach((point, i) => {
                const x = this.worldToScreenX(point.x);
                const y = this.worldToScreenY(point.y);
                
                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            
            ctx.stroke();
        });
    }
    
    drawVehicles() {
        const ctx = this.ctx;
        
        this.trajectories.forEach((traj, index) => {
            const points = traj.trajectory;
            
            let state = null;
            for (let i = 0; i < points.length - 1; i++) {
                if (points[i].time <= this.currentTime && points[i + 1].time >= this.currentTime) {
                    const t = (this.currentTime - points[i].time) / (points[i + 1].time - points[i].time);
                    state = this.interpolateState(points[i], points[i + 1], t);
                    break;
                }
            }
            
            if (!state && points.length > 0) {
                if (this.currentTime < points[0].time) {
                    state = { ...points[0] };
                } else {
                    state = { ...points[points.length - 1] };
                }
            }
            
            if (state) {
                this.drawVehicle(state, this.vehicles[index]?.color || '#3498db');
            }
        });
    }
    
    drawVehicle(state, color) {
        const ctx = this.ctx;
        const x = this.worldToScreenX(state.x);
        const y = this.worldToScreenY(state.y);
        const theta = state.theta;
        const length = state.length * this.scale;
        const width = state.width * this.scale;
        
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(-theta);
        
        ctx.fillStyle = color;
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1;
        
        ctx.beginPath();
        ctx.roundRect(-length / 2, -width / 2, length, width, 4);
        ctx.fill();
        ctx.stroke();
        
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.fillRect(length / 6, -width / 2 + 2, length / 4, width - 4);
        
        ctx.fillStyle = '#fff';
        ctx.beginPath();
        ctx.arc(length / 2 - 4, -width / 2 + 4, 2, 0, Math.PI * 2);
        ctx.arc(length / 2 - 4, width / 2 - 4, 2, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.fillStyle = '#ff6b6b';
        ctx.beginPath();
        ctx.arc(-length / 2 + 4, -width / 2 + 4, 2, 0, Math.PI * 2);
        ctx.arc(-length / 2 + 4, width / 2 - 4, 2, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.restore();
    }
    
    interpolateState(s1, s2, t) {
        return {
            x: s1.x + (s2.x - s1.x) * t,
            y: s1.y + (s2.y - s1.y) * t,
            v: s1.v + (s2.v - s1.v) * t,
            theta: s1.theta + (s2.theta - s1.theta) * t,
            length: s1.length,
            width: s1.width
        };
    }
    
    worldToScreenX(x) {
        return this.offsetX + x * this.scale;
    }
    
    worldToScreenY(y) {
        return this.offsetY - y * this.scale;
    }
    
    async checkSystemStatus() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            document.getElementById('apiStatus').classList.add('active');
            
            if (data.redis_available) {
                document.getElementById('redisStatus').classList.add('active');
            }
        } catch (err) {
            console.error('健康检查失败:', err);
        }
    }
    
    async startComputation() {
        if (this.vehicles.length < 2) {
            alert('至少需要两辆车才能计算碰撞概率');
            return;
        }
        
        const simCount = parseInt(document.getElementById('simCount').value) || 100000;
        const dt = parseFloat(document.getElementById('timeStep').value) || 0.01;
        const tMax = parseFloat(document.getElementById('maxTime').value) || 30;
        const baseSeed = parseInt(document.getElementById('baseSeed').value) || 42;
        
        document.getElementById('resultSection').style.display = 'block';
        document.getElementById('progressContainer').style.display = 'block';
        document.getElementById('progressFill').style.width = '0%';
        document.getElementById('progressText').textContent = '0%';
        document.getElementById('resultBox').style.opacity = '0.5';
        
        document.getElementById('computeBtn').disabled = true;
        document.getElementById('computeBtn').textContent = '⏳ 计算中...';
        
        try {
            const response = await fetch('/api/compute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vehicles: this.vehicles,
                    road_condition: this.roadCondition,
                    num_simulations: simCount,
                    dt: dt,
                    t_max: tMax,
                    base_seed: baseSeed
                })
            });
            
            const data = await response.json();
            
            if (data.from_cache && data.status === 'completed') {
                this.displayResult(data.result);
                document.getElementById('computeBtn').disabled = false;
                document.getElementById('computeBtn').textContent = '🚀 开始碰撞概率计算';
                return;
            }
            
            this.currentTaskId = data.task_id;
            this.pollStatus();
        } catch (err) {
            console.error('开始计算失败:', err);
            alert('计算请求失败，请检查后端服务是否运行');
            document.getElementById('computeBtn').disabled = false;
            document.getElementById('computeBtn').textContent = '🚀 开始碰撞概率计算';
        }
    }
    
    pollStatus() {
        if (!this.currentTaskId) return;
        
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
        
        this.pollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/status/${this.currentTaskId}`);
                const data = await response.json();
                
                const progress = data.progress || 0;
                document.getElementById('progressFill').style.width = progress + '%';
                document.getElementById('progressText').textContent = progress + '%';
                
                if (data.status === 'completed') {
                    clearInterval(this.pollingInterval);
                    this.pollingInterval = null;
                    
                    const resultResponse = await fetch(`/api/result/${this.currentTaskId}`);
                    const resultData = await resultResponse.json();
                    
                    if (resultData.status === 'completed') {
                        this.displayResult(resultData.result);
                    }
                    
                    document.getElementById('computeBtn').disabled = false;
                    document.getElementById('computeBtn').textContent = '🚀 开始碰撞概率计算';
                }
            } catch (err) {
                console.error('轮询状态失败:', err);
            }
        }, 500);
    }
    
    displayResult(result) {
        document.getElementById('resultBox').style.opacity = '1';
        
        const prob = result.collision_probability * 100;
        document.getElementById('collisionProb').textContent = prob.toFixed(4) + '%';
        
        if (result.confidence_interval_95_low !== undefined) {
            const ciLow = result.confidence_interval_95_low * 100;
            const ciHigh = result.confidence_interval_95_high * 100;
            document.getElementById('confidenceInterval').textContent = 
                `[${ciLow.toFixed(4)}%, ${ciHigh.toFixed(4)}%]`;
        }
        
        document.getElementById('collisionCount').textContent = result.collision_count.toLocaleString();
        document.getElementById('simulationCount').textContent = result.num_simulations.toLocaleString();
        
        if (result.mean_collision_time !== undefined) {
            document.getElementById('timeStats').style.display = 'flex';
            document.getElementById('meanCollisionTime').textContent = 
                result.mean_collision_time.toFixed(2) + 's';
        } else {
            document.getElementById('timeStats').style.display = 'none';
        }
    }
    
    async startComparison() {
        if (this.vehicles.length < 2) {
            alert('至少需要两辆车才能进行对比计算');
            return;
        }
        
        const simCount = parseInt(document.getElementById('simCount').value) || 100000;
        const dt = parseFloat(document.getElementById('timeStep').value) || 0.01;
        const tMax = parseFloat(document.getElementById('maxTime').value) || 30;
        const baseSeed = parseInt(document.getElementById('baseSeed').value) || 42;
        
        document.getElementById('compareSection').style.display = 'block';
        document.getElementById('compareProgressContainer').style.display = 'block';
        document.getElementById('compareProgressFill').style.width = '0%';
        document.getElementById('compareProgressText').textContent = '0%';
        document.getElementById('compareTableContainer').style.opacity = '0.5';
        document.getElementById('compareNote').style.display = 'none';
        
        document.getElementById('compareBtn').disabled = true;
        document.getElementById('compareBtn').textContent = '⏳ 对比计算中...';
        
        try {
            const response = await fetch('/api/compute/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vehicles: this.vehicles,
                    conditions: this.compareConditions,
                    num_simulations: simCount,
                    dt: dt,
                    t_max: tMax,
                    base_seed: baseSeed
                })
            });
            
            const data = await response.json();
            this.compareTaskId = data.comparison_id;
            this.pollCompareStatus();
        } catch (err) {
            console.error('对比计算失败:', err);
            alert('对比计算请求失败，请检查后端服务是否运行');
            document.getElementById('compareBtn').disabled = false;
            document.getElementById('compareBtn').textContent = '📊 多路面场景垂直对比';
        }
    }
    
    pollCompareStatus() {
        if (!this.compareTaskId) return;
        
        if (this.comparePollingInterval) {
            clearInterval(this.comparePollingInterval);
        }
        
        this.comparePollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/compare/status/${this.compareTaskId}`);
                const data = await response.json();
                
                const progress = data.progress || 0;
                document.getElementById('compareProgressFill').style.width = progress + '%';
                document.getElementById('compareProgressText').textContent = progress + '%';
                
                if (data.status === 'completed') {
                    clearInterval(this.comparePollingInterval);
                    this.comparePollingInterval = null;
                    
                    const resultResponse = await fetch(`/api/compare/result/${this.compareTaskId}`);
                    const resultData = await resultResponse.json();
                    
                    this.renderCompareTable(resultData);
                    
                    document.getElementById('compareBtn').disabled = false;
                    document.getElementById('compareBtn').textContent = '📊 多路面场景垂直对比';
                    document.getElementById('compareNote').style.display = 'block';
                }
            } catch (err) {
                console.error('轮询对比状态失败:', err);
            }
        }, 500);
    }
    
    renderCompareTable(data) {
        document.getElementById('compareTableContainer').style.opacity = '1';
        
        const tbody = document.getElementById('compareTableBody');
        tbody.innerHTML = '';
        
        const results = data.results || {};
        const baseline = data.baseline || 'dry_asphalt';
        const conditions = data.conditions || this.compareConditions;
        
        conditions.forEach((cond) => {
            const result = results[cond];
            const road = this.roadConditions[cond] || { name: cond, icon: '🚗' };
            
            const tr = document.createElement('tr');
            if (cond === baseline) {
                tr.className = 'baseline';
            }
            
            let probText = '-';
            let changeText = '-';
            let changeClass = 'change-neutral';
            let timeText = '-';
            let ciText = '-';
            let countText = '-';
            
            if (result) {
                const prob = result.collision_probability * 100;
                probText = prob.toFixed(2) + '%';
                
                if (result.confidence_interval_95_low !== undefined && 
                    result.confidence_interval_95_high !== undefined) {
                    const ciLow = result.confidence_interval_95_low * 100;
                    const ciHigh = result.confidence_interval_95_high * 100;
                    ciText = `[${ciLow.toFixed(2)}%, ${ciHigh.toFixed(2)}%]`;
                }
                
                if (result.collision_count !== undefined && 
                    result.num_simulations !== undefined) {
                    countText = `${result.collision_count} / ${result.num_simulations}`;
                }
                
                if (result.change_from_baseline_pct !== undefined && cond !== baseline) {
                    const change = result.change_from_baseline_pct;
                    const absChange = result.change_absolute * 100;
                    if (change > 0) {
                        changeText = `↑ +${change.toFixed(1)}% (+${absChange.toFixed(2)}pp)`;
                        changeClass = 'change-increase';
                    } else if (change < 0) {
                        changeText = `↓ ${change.toFixed(1)}% (${absChange.toFixed(2)}pp)`;
                        changeClass = 'change-decrease';
                    } else {
                        changeText = '—';
                    }
                } else if (cond === baseline) {
                    changeText = '基准';
                }
                
                if (result.mean_collision_time !== undefined) {
                    timeText = result.mean_collision_time.toFixed(2) + 's';
                }
            }
            
            tr.innerHTML = `
                <td>
                    <span class="road-icon">${road.icon}</span>
                    ${road.name}
                </td>
                <td class="prob-value">${probText}</td>
                <td class="ci-value">${ciText}</td>
                <td class="${changeClass}">${changeText}</td>
                <td class="count-value">${countText}</td>
                <td class="time-value">${timeText}</td>
            `;
            
            tbody.appendChild(tr);
        });
    }
}

if (!CanvasRenderingContext2D.prototype.roundRect) {
    CanvasRenderingContext2D.prototype.roundRect = function(x, y, width, height, radius) {
        if (typeof radius === 'number') {
            radius = {tl: radius, tr: radius, br: radius, bl: radius};
        }
        this.beginPath();
        this.moveTo(x + radius.tl, y);
        this.lineTo(x + width - radius.tr, y);
        this.quadraticCurveTo(x + width, y, x + width, y + radius.tr);
        this.lineTo(x + width, y + height - radius.br);
        this.quadraticCurveTo(x + width, y + height, x + width - radius.br, y + height);
        this.lineTo(x + radius.bl, y + height);
        this.quadraticCurveTo(x, y + height, x, y + height - radius.bl);
        this.lineTo(x, y + radius.tl);
        this.quadraticCurveTo(x, y, x + radius.tl, y);
        this.closePath();
        return this;
    };
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new CollisionSimulationApp();
});
