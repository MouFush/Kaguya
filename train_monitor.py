"""
DeepSeek-V3 训练监控面板
实时监测GPU使用率和训练进度
独立运行，不影响训练进程
"""

import subprocess
import time
import os
import json
import re
from datetime import datetime

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_gpu_info():
    """获取GPU信息"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=timestamp,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,power.limit,fan.speed', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, encoding='utf-8'
        )
        parts = [p.strip() for p in result.stdout.strip().split(',')]
        return {
            'timestamp': parts[0] if len(parts) > 0 else 'N/A',
            'temp': float(parts[1]) if len(parts) > 1 else 0,
            'gpu_util': float(parts[2]) if len(parts) > 2 else 0,
            'mem_util': float(parts[3]) if len(parts) > 3 else 0,
            'mem_used': float(parts[4]) if len(parts) > 4 else 0,
            'mem_total': float(parts[5]) if len(parts) > 5 else 0,
            'power_draw': float(parts[6]) if len(parts) > 6 else 0,
            'power_limit': float(parts[7]) if len(parts) > 7 else 0,
            'fan_speed': float(parts[8]) if len(parts) > 8 else 0,
        }
    except Exception as e:
        return None

def get_process_info():
    """获取GPU进程信息"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, encoding='utf-8'
        )
        processes = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split(',')
                if len(parts) >= 3:
                    processes.append({
                        'pid': parts[0].strip(),
                        'name': parts[1].strip()[-40:],
                        'mem': parts[2].strip()
                    })
        return processes
    except:
        return []

def get_training_status():
    """获取训练状态"""
    checkpoint_dir = r'c:\Users\林智涵\.conda\checkpoints'
    status = {
        'has_checkpoint': False,
        'epoch': 0,
        'best_loss': float('inf'),
        'last_update': 'N/A'
    }
    
    # 检查最佳模型
    best_model_path = os.path.join(checkpoint_dir, 'best_model.pt')
    if os.path.exists(best_model_path):
        status['has_checkpoint'] = True
        try:
            mtime = os.path.getmtime(best_model_path)
            status['last_update'] = datetime.fromtimestamp(mtime).strftime('%H:%M:%S')
            
            # 尝试读取checkpoint信息
            checkpoint = torch_load_lite(best_model_path)
            if checkpoint:
                status['epoch'] = checkpoint.get('epoch', 0)
                status['best_loss'] = checkpoint.get('val_loss', float('inf'))
        except:
            pass
    
    return status

def torch_load_lite(path):
    """轻量级加载checkpoint（只读取元数据）"""
    try:
        import torch
        checkpoint = torch.load(path, map_location='cpu', weights_only=False)
        return {
            'epoch': checkpoint.get('epoch', 0),
            'val_loss': checkpoint.get('val_loss', float('inf')),
            'global_step': checkpoint.get('global_step', 0)
        }
    except:
        return None

def draw_bar(value, max_value, width=20, filled='█', empty='░'):
    """绘制进度条"""
    if max_value <= 0:
        return empty * width
    ratio = min(value / max_value, 1.0)
    filled_count = int(ratio * width)
    return filled * filled_count + empty * (width - filled_count)

def get_status_emoji(value, thresholds=[30, 70]):
    """根据值返回状态表情"""
    if value < thresholds[0]:
        return '🔴'
    elif value < thresholds[1]:
        return '🟡'
    else:
        return '🟢'

def monitor(refresh_interval=2):
    """主监控循环"""
    print("启动训练监控面板...")
    time.sleep(1)
    
    iteration = 0
    gpu_history = []
    
    try:
        while True:
            clear_screen()
            iteration += 1
            
            # 获取GPU信息
            gpu = get_gpu_info()
            processes = get_process_info()
            training = get_training_status()
            
            # 记录历史
            if gpu:
                gpu_history.append(gpu['gpu_util'])
                if len(gpu_history) > 30:
                    gpu_history.pop(0)
            
            # 绘制界面
            print("╔" + "═" * 68 + "╗")
            print("║" + " DeepSeek-V3 训练监控面板 ".center(66) + "║")
            print("╠" + "═" * 68 + "╣")
            
            if gpu:
                mem_percent = (gpu['mem_used'] / gpu['mem_total']) * 100 if gpu['mem_total'] > 0 else 0
                power_percent = (gpu['power_draw'] / gpu['power_limit']) * 100 if gpu['power_limit'] > 0 else 0
                
                print(f"║ 时间: {gpu['timestamp']}" + " " * (66 - len(gpu['timestamp']) - 6) + "║")
                print("╠" + "─" * 68 + "╣")
                
                # GPU利用率
                status = get_status_emoji(gpu['gpu_util'], [30, 70])
                bar = draw_bar(gpu['gpu_util'], 100, 25)
                print(f"║ {status} GPU利用率: {gpu['gpu_util']:>5.1f}%  [{bar}]     ║")
                
                # 显存使用
                status = get_status_emoji(mem_percent, [50, 90])
                bar = draw_bar(mem_percent, 100, 25)
                print(f"║ {status} 显存使用:   {mem_percent:>5.1f}%  [{bar}]     ║")
                
                # 温度
                temp_status = '🟢' if gpu['temp'] < 70 else '🟡' if gpu['temp'] < 80 else '🔴'
                print(f"║ {temp_status} 温度: {gpu['temp']:>5.0f}°C    风扇: {gpu['fan_speed']:>5.0f}%    功耗: {gpu['power_draw']:>5.0f}W/{gpu['power_limit']:>5.0f}W  ║")
                
                # 显存详情
                print(f"║ 💾 显存: {gpu['mem_used']:>6.0f}MB / {gpu['mem_total']:>6.0f}MB                              ║")
                
                # GPU历史趋势
                if len(gpu_history) >= 10:
                    avg_util = sum(gpu_history) / len(gpu_history)
                    min_util = min(gpu_history)
                    max_util = max(gpu_history)
                    print(f"║ 📊 GPU历史: 平均 {avg_util:>5.1f}% | 最低 {min_util:>5.1f}% | 最高 {max_util:>5.1f}%     ║")
            
            print("╠" + "═" * 68 + "╣")
            print("║ 运行中的GPU进程:".ljust(67) + "║")
            print("╠" + "─" * 68 + "╣")
            
            if processes:
                for p in processes[:3]:
                    name = p['name'][:35]
                    print(f"║ PID: {p['pid']:<8} {name:<35} {p['mem']:>6}MB ║")
            else:
                print("║ 无GPU进程运行".ljust(67) + "║")
            
            print("╠" + "═" * 68 + "╣")
            print("║ 训练状态:".ljust(67) + "║")
            print("╠" + "─" * 68 + "╣")
            
            if training['has_checkpoint']:
                print(f"║ ✅ 已有检查点  |  Epoch: {training['epoch']:<3} |  最佳损失: {training['best_loss']:.4f}  |  更新: {training['last_update']} ║")
            else:
                print("║ ⏳ 等待训练开始或尚未保存检查点".ljust(67) + "║")
            
            print("╠" + "═" * 68 + "╣")
            
            # 训练配置信息
            print("║ 训练配置:".ljust(67) + "║")
            print("║ 模型参数: ~178M  |  批次: 128  |  序列长度: 128  |  混合精度: ✅ ║")
            print("║ 数据集: LCCC (85.5万对话对)  |  训练轮数: 10".ljust(67) + "║")
            
            print("╚" + "═" * 68 + "╝")
            print(f"\n刷新间隔: {refresh_interval}秒 | 刷新次数: {iteration} | 按 Ctrl+C 退出")
            
            time.sleep(refresh_interval)
            
    except KeyboardInterrupt:
        print("\n\n监控已停止")

if __name__ == "__main__":
    monitor(refresh_interval=2)
