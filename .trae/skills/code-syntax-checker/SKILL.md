---
name: "code-syntax-checker"
description: "Compares user-written code with reference examples and validates syntax correctness. Invoke when user wants to practice coding, check syntax, or compare their code with correct examples."
---

# Code Syntax Checker

This skill helps users learn coding by comparing their written code with reference examples and validating syntax correctness.

## When to Invoke

Invoke this skill when:
- User wants to practice writing code and check correctness
- User asks to compare their code with a reference
- User wants syntax validation
- User is learning a new programming concept and wants hands-on practice

## Features

1. **Side-by-Side Comparison**: Display user code alongside reference code
2. **Syntax Validation**: Check for syntax errors using language diagnostics
3. **Diff Highlighting**: Highlight differences between user and reference code
4. **Error Explanation**: Provide detailed explanations for syntax errors
5. **Correction Suggestions**: Suggest fixes for identified issues

## Usage Format

### For Python Code

```python
# ==================== 编写区域 ====================
# 请在下方编写你的代码：

def my_function(x):
    # 你的实现
    
# ==================== 对照区域 ====================
# 参考实现：

def my_function(x):
    return x * 2

# ==================== 检查结果 ====================
# 语法检查: ✓ 正确 / ✗ 错误
# 差异分析: ...
# 修正建议: ...
```

### For Multiple Languages

Supports:
- Python
- JavaScript/TypeScript
- Java
- C/C++
- Go
- Rust

## Implementation Steps

1. **Create Practice Template**
   - Provide a coding exercise with clear requirements
   - Include a reference implementation (hidden initially)
   
2. **User Writes Code**
   - User writes their implementation in the designated area
   - Code is validated in real-time if possible

3. **Comparison & Validation**
   - Compare user code with reference
   - Run syntax checker (using GetDiagnostics)
   - Highlight differences

4. **Feedback Generation**
   - List syntax errors with line numbers
   - Explain what's wrong and why
   - Provide correction suggestions

## Example Interaction

```
User: 我想练习Python函数，帮我检查代码

AI: 好的！让我们来练习。

## 练习：实现一个计算斐波那契数列的函数

要求：
- 函数名：fibonacci
- 参数：n (整数)
- 返回：第n个斐波那契数

### 编写区域
```python
def fibonacci(n):
    # 请在此编写你的代码
    pass
```

### 检查结果
请先编写代码，然后告诉我"检查"，我会帮你验证。

---
User: 我写好了
```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

AI: 
### 对照检查结果

#### 你的代码：
```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

#### 参考实现：
```python
def fibonacci(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

#### 语法检查：✓ 正确

#### 差异分析：
| 项目 | 你的代码 | 参考代码 | 状态 |
|------|----------|----------|------|
| 负数处理 | 无 | 有异常处理 | 可改进 |
| 基本逻辑 | ✓ | ✓ | 正确 |

#### 评价：
你的实现基本正确！递归逻辑清晰。
建议：可以添加对负数输入的处理，使函数更健壮。
```

## Best Practices

1. **Progressive Difficulty**: Start with simple exercises, gradually increase complexity
2. **Encourage First**: Always acknowledge correct parts before pointing out issues
3. **Explain Why**: Don't just show correct code, explain the reasoning
4. **Multiple Solutions**: Show that there can be different valid approaches
5. **Real-time Feedback**: Use GetDiagnostics for immediate syntax validation

## Diagnostic Tools

Use `GetDiagnostics` tool to check for:
- Syntax errors
- Type errors
- Linting issues
- Import errors

## Output Format

```markdown
### 检查结果

#### 语法检查：[✓ 正确 / ✗ 发现问题]

#### 问题列表：
1. [行号] 问题描述
   - 错误代码：...
   - 修正建议：...

#### 与参考对照：
| 差异点 | 你的代码 | 参考代码 |
|--------|----------|----------|
| ... | ... | ... |

#### 总体评价：
...
```
