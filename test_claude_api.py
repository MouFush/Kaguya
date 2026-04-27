"""
测试 Claude API 配置
"""

import asyncio
import sys
from claude_client import ClaudeClient, ClaudeMessage, quick_chat


async def test_models():
    """测试所有可用模型"""
    print("=" * 60)
    print("Claude API 测试工具")
    print("=" * 60)

    client = ClaudeClient()

    # 显示可用模型
    print("\n📋 可用模型列表:")
    models = client.get_available_models()
    for model_id, info in models.items():
        print(f"  • {info['name']}")
        print(f"    ID: {model_id}")
        print(f"    描述: {info['description']}")
        print(f"    支持视觉: {'✅' if info['supports_vision'] else '❌'}")
        print()

    # 测试简单对话
    print("\n🧪 测试简单对话 (claude-sonnet-4-6):")
    print("-" * 60)

    try:
        response = await client.simple_chat(
            prompt="你好！请用一句话介绍自己。",
            model="claude-sonnet-4-6",
            temperature=0.7
        )
        print(f"✅ 成功!")
        print(f"回复: {response}")
    except Exception as e:
        print(f"❌ 失败: {e}")

    # 测试带上下文的对话
    print("\n🧪 测试带上下文的对话:")
    print("-" * 60)

    try:
        messages = [
            ClaudeMessage(role="system", content="你是一个专业的Python编程助手。"),
            ClaudeMessage(role="user", content="什么是异步编程？"),
        ]

        response = await client.chat(
            messages=messages,
            model="claude-sonnet-4-6",
            temperature=0.7
        )
        print(f"✅ 成功!")
        print(f"回复: {response.content[:200]}...")
        print(f"模型: {response.model}")
        print(f"用量: {response.usage}")
    except Exception as e:
        print(f"❌ 失败: {e}")

    # 测试流式输出
    print("\n🧪 测试流式输出:")
    print("-" * 60)

    try:
        messages = [
            ClaudeMessage(role="user", content="用3个要点说明Python的优点")
        ]

        print("回复: ", end="", flush=True)
        async for chunk in client.chat_stream(
            messages=messages,
            model="claude-haiku-4-5",
            temperature=0.7
        ):
            print(chunk, end="", flush=True)
        print("\n✅ 流式输出成功!")
    except Exception as e:
        print(f"\n❌ 失败: {e}")

    await client.close()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


async def interactive_chat():
    """交互式聊天"""
    print("\n🤖 Claude 交互式聊天")
    print("输入 'quit' 退出, 'models' 查看模型, 'clear' 清空历史\n")

    client = ClaudeClient()
    messages = []
    current_model = "claude-sonnet-4-6"

    while True:
        try:
            user_input = input("\n👤 你: ").strip()

            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'models':
                print("\n可用模型:")
                for model_id, info in client.get_available_models().items():
                    marker = " 👈 当前" if model_id == current_model else ""
                    print(f"  - {info['name']}: {model_id}{marker}")
                continue
            elif user_input.lower().startswith('model '):
                new_model = user_input[6:].strip()
                if new_model in client.get_available_models():
                    current_model = new_model
                    print(f"✅ 已切换到模型: {new_model}")
                else:
                    print(f"❌ 未知模型: {new_model}")
                continue
            elif user_input.lower() == 'clear':
                messages = []
                print("✅ 历史已清空")
                continue
            elif not user_input:
                continue

            messages.append(ClaudeMessage(role="user", content=user_input))

            print("\n🤖 Claude: ", end="", flush=True)

            # 使用流式输出
            full_response = ""
            async for chunk in client.chat_stream(
                messages=messages,
                model=current_model,
                temperature=0.7
            ):
                print(chunk, end="", flush=True)
                full_response += chunk

            print()  # 换行
            messages.append(ClaudeMessage(role="assistant", content=full_response))

        except KeyboardInterrupt:
            print("\n\n再见!")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")

    await client.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_chat())
    else:
        asyncio.run(test_models())
        print("\n💡 提示: 运行 `python test_claude_api.py --interactive` 进入交互模式")
