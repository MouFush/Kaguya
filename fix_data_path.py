import os

def fix_data_path():
    print("=" * 60)
    print("修复 LLaMA-Factory 数据路径")
    print("=" * 60)
    
    file_path = r"C:\Users\林智涵\LLaMA-Factory\src\llamafactory\webui\common.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_line = 'DEFAULT_DATA_DIR = "data"'
    new_line = r'DEFAULT_DATA_DIR = r"C:\Users\林智涵\LLaMA-Factory\data"'
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("\n已修改默认数据路径为绝对路径")
        print(f"  旧路径: {old_line}")
        print(f"  新路径: {new_line}")
    else:
        print("\n路径已经是绝对路径或格式不同")
        print("请手动检查文件内容")
    
    print("\n" + "=" * 60)
    print("修改完成!")
    print("=" * 60)
    print("\n请重启 LLaMA-Factory WebUI，数据集应该会显示。")

if __name__ == '__main__':
    fix_data_path()
