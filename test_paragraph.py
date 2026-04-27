import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

print('Loading model...')
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type='nf4',
    bnb_4bit_use_double_quant=True
)
tokenizer = AutoTokenizer.from_pretrained(r'C:\Users\林智涵\.cache\modelscope\hub\models\Qwen\Qwen3___5-9B', trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    r'C:\Users\林智涵\.cache\modelscope\hub\models\Qwen\Qwen3___5-9B',
    quantization_config=quantization_config,
    device_map='auto',
    trust_remote_code=True
)
print('Model loaded!')

system_prompt = '''你是一个温柔可爱的AI助手。

【重要规则 - 必须遵守】
你的回复必须是连贯的自然段落形式！绝对禁止使用列表、要点、数字标记！

错误示例（禁止）：
- 第一点...
- 第二点...
1. 首先...
2. 然后...

正确示例（必须）：
首先呢，让我来解释一下这个问题。这是一个很有趣的话题...

接下来我想说的是，这个概念其实并不难理解...

最后呀，希望我的解释对你有帮助~

【说话风格】
- 语气温柔、亲切，像邻家大姐姐一样
- 使用"呢~"、"呀~"、"哦~"等语气词
- 适当使用可爱的表情符号
- 称呼用户为"亲"或"小伙伴"

【格式要求】
- 每个段落之间必须空一行
- 每段聚焦一个主题
- 用过渡词连接段落

请用温柔可爱的自然段落方式回复用户的问题~'''

messages = [
    {'role': 'system', 'content': system_prompt},
    {'role': 'user', 'content': '请介绍一下Python语言'}
]

text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer([text], return_tensors='pt').to(model.device)

with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=500, do_sample=True, temperature=0.7, top_p=0.9, pad_token_id=tokenizer.eos_token_id)

generated_ids = outputs[0][inputs.input_ids.shape[1]:]
response = tokenizer.decode(generated_ids, skip_special_tokens=True)

print('\n' + '='*60)
print('模型回复:')
print('='*60)
print(response)
print('='*60)
print('\n换行符数量:', response.count('\n'))
