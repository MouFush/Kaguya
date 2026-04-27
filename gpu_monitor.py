"""
GPU实时监控工具
独立运行，不影响训练进程
"""

import subprocess
import time
import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_gpu_info():
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=timestamp,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,power.limit', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, encoding='utf-8'
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_process_info():
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, encoding='utf-8'
        )
        return result.stdout.strip()
    except:
        return ""

def monitor_gpu(refresh_interval=1):
    print("GPU实时监控 (按Ctrl+C退出)")
    print("=" * 60)
    
    try:
        while True:
            clear_screen()
            print("╔" + "═" * 58 + "╗")
            print("║" + " GPU实时监控 ".center(56) + "║")
            print("╠" + "═" * 58 + "╣")
            
            gpu_info = get_gpu_info()
            if gpu_info and not gpu_info.startswith("Error"):
                parts = [p.strip() for p in gpu_info.split(',')]
                if len(parts) >= 8:
                    timestamp = parts[0]
                    temp = float(parts[1])
                    gpu_util = float(parts[2])
                    mem_util = float(parts[3])
                    mem_used = float(parts[4])
                    mem_total = float(parts[5])
                    power_draw = float(parts[6])
                    power_limit = float(parts[7])
                    
                    mem_percent = (mem_used / mem_total) * 100
                    power_percent = (power_draw / power_limit) * 100
                    
                    # 温度状态
                    temp_status = "🟢" if temp < 70 else "🟡" if temp < 80 else "🔴"
                    
                    # GPU利用率状态
                    util_status = "🟢" if gpu_util > 50 else "🟡" if gpu_util > 20 else "🔴"
                    
                    print(f"║ 时间: {timestamp}" + " " * (56 - len(timestamp) - 6) + "║")
                    print("╠" + "─" * 58 + "╣")
                    print(f"║ {temp_status} 温度: {temp:>5.0f}°C                                    ║")
                    print(f"║ {util_status} GPU利用率: {gpu_util:>5.0f}%   [{'█' * int(gpu_util/5)}{' ' * (20-int(gpu_util/5))}]    ║")
                    print(f"║ 📊 显存使用: {mem_percent:>5.1f}%   [{'█' * int(mem_percent/5)}{' ' * (20-int(mem_percent/5))}]    ║")
                    print(f"║ 💾 显存: {mem_used:>6.0f}MB / {mem_total:>6.0f}MB                      ║")
                    print(f"║ ⚡ 功耗: {power_draw:>5.0f}W / {power_limit:>5.0f}W ({power_percent:>3.0f}%)                ║")
            
            print("╠" + "═" * 58 + "╣")
            print("║ 运行中的GPU进程:                                        ║")
            print("╠" + "─" * 58 + "╣")
            
            process_info = get_process_info()
            if process_info:
                for line in process_info.split('\n'):
                    if line.strip():
                        parts = line.split(',')
                        if len(parts) >= 3:
                            pid = parts[0].strip()
                            name = parts[1].strip()[-30:]  # 截取最后30个字符
                            mem = parts[2].strip()
                            print(f"║ PID: {pid:<8} {name:<30} {mem:>6}MB ║")
            else:
                print("║ 无GPU进程运行                                            ║")
            
            print("╚" + "═" * 58 + "╝")
            print(f"\n刷新间隔: {refresh_interval}秒 | 按Ctrl+C退出")
            
            time.sleep(refresh_interval)
            
    except KeyboardInterrupt:
        print("\n\n监控已停止")

if __name__ == "__main__":
    monitor_gpu(refresh_interval=2)
