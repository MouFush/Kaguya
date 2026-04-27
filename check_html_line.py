import urllib.request

# 获取页面HTML
try:
    response = urllib.request.urlopen('http://127.0.0.1:5000/')
    html = response.read().decode('utf-8')

    # 保存到文件
    with open('server_output.html', 'w', encoding='utf-8') as f:
        f.write(html)

    # 检查第3335行
    lines = html.split('\n')
    print(f"HTML总行数: {len(lines)}")
    
    if len(lines) > 3335:
        print(f"\n第3334行:")
        print(f"{lines[3334][:150]}")
        print(f"\n第3335行:")
        print(f"{lines[3335][:150]}")
        print(f"\n第3336行:")
        print(f"{lines[3336][:150]}")
        
        # 显示第3335行第51列附近的字符
        line = lines[3335]
        if len(line) > 51:
            print(f"\n第3335行第45-60列:")
            print(f"'{line[44:60]}'")
            print(f"字符编码: {[ord(c) for c in line[44:60]]}")
    else:
        print(f"HTML只有 {len(lines)} 行，不足3335行")
        # 显示最后几行
        print(f"\n最后5行:")
        for i in range(max(0, len(lines)-5), len(lines)):
            print(f"{i}: {lines[i][:100]}")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
