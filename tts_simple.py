"""
Qwen3.5-9B 语音合成脚本
使用Edge-TTS生成语音
"""

import os
import sys
import asyncio

def text_to_speech_edge(text, output_path, voice="zh-CN-XiaoxiaoNeural"):
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        asyncio.run(communicate.save(output_path))
        return os.path.exists(output_path)
    except Exception as e:
        print(f"Edge-TTS错误: {e}")
        return False

def text_to_voice(text, output_path):
    print("使用Edge-TTS生成语音...")
    if text_to_speech_edge(text, output_path):
        print(f"语音已保存到: {output_path}")
        return output_path
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python tts_simple.py <文本> [输出文件]")
        sys.exit(1)
    
    text = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "output.mp3"
    
    result = text_to_voice(text, output)
    if result:
        print(f"SUCCESS: {result}")
    else:
        print("FAILED")
