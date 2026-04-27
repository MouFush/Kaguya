import os

def fix_wsl_path():
    print("=" * 60)
    print("修复 WSL 中的数据路径")
    print("=" * 60)
    
    file_path = r"C:\Users\林智涵\LLaMA-Factory\src\llamafactory\webui\common.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n当前路径配置:")
    for line in content.split('\n'):
        if 'DEFAULT_DATA_DIR' in line:
            print(f"  {line.strip()}")
    
    old_path = r'DEFAULT_DATA_DIR = r"C:\Users\林智涵\LLaMA-Factory\data"'
    new_path = 'DEFAULT_DATA_DIR = "/mnt/c/Users/林智涵/LLaMA-Factory/data"'
    
    if old_path in content:
        content = content.replace(old_path, new_path)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("\n已修改为 WSL 兼容路径:")
        print(f"  {new_path}")
    else:
        print("\n路径格式不同，尝试其他匹配...")
        import re
        pattern = r'DEFAULT_DATA_DIR\s*=\s*["\']?[^"\']+["\']?'
        match = re.search(pattern, content)
        if match:
            print(f"  找到: {match.group()}")
            content = re.sub(pattern, new_path, content)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  已替换为: {new_path}")
    
    print("\n" + "=" * 60)
    print("修改完成!")
    print("=" * 60)
    print("\n请重启 LLaMA-Factory WebUI")

if __name__ == '__main__':
    fix_wsl_path()
