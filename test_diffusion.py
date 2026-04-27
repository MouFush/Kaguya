"""
Diffusion Model 测试脚本
"""
import torch
import torch.nn as nn
import sys

# 导入实现的模块
from diffusion_model import SimpleUNet, DiffusionModel, SinusoidalPositionEmbeddings, Block

print('=' * 70)
print('Diffusion Model 结构测试')
print('=' * 70)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'使用设备: {device}')

# 测试U-Net模型
print('\n' + '-' * 70)
print('测试 SimpleUNet 结构')
print('-' * 70)
model = SimpleUNet(in_channels=1, time_emb_dim=32).to(device)
total_params = sum(p.numel() for p in model.parameters())
print(f'模型参数量: {total_params:,}')

# 测试前向传播
x = torch.randn(4, 1, 28, 28).to(device)
t = torch.randint(0, 1000, (4,)).to(device)
output = model(x, t)
print(f'输入形状:  {x.shape}')
print(f'时间步:    {t.shape}')
print(f'输出形状:  {output.shape}')
assert output.shape == x.shape, '输出形状错误'
print('✅ U-Net前向传播测试通过')

# 测试DiffusionModel
print('\n' + '-' * 70)
print('测试 DiffusionModel 扩散过程')
print('-' * 70)
diffusion = DiffusionModel(timesteps=1000, device=device)
print(f'时间步数: {diffusion.timesteps}')
print(f'beta范围: [{diffusion.betas[0]:.6f}, {diffusion.betas[-1]:.6f}]')

# 测试前向加噪
x_start = torch.randn(2, 1, 28, 28).to(device)
t = torch.tensor([0, 500]).to(device)
x_t, noise = diffusion.q_sample(x_start, t)
print(f'\n前向扩散测试:')
print(f'  原始图像: {x_start.shape}')
print(f'  时间步:   {t}')
print(f'  加噪后:   {x_t.shape}')
print(f'  噪声:     {noise.shape}')

# 测试损失计算
t_rand = torch.randint(0, 1000, (2,)).to(device)
loss = diffusion.p_losses(model, x_start, t_rand)
print(f'\n损失值: {loss.item():.6f}')
print('✅ 扩散过程测试通过')

# 测试采样（只采样10步以节省时间）
print('\n' + '-' * 70)
print('测试采样过程（10步）')
print('-' * 70)
diffusion_short = DiffusionModel(timesteps=10, device=device)
model.eval()
with torch.no_grad():
    sample = diffusion_short.sample(model, batch_size=2, channels=1, img_size=28)
print(f'生成样本形状: {sample.shape}')
print('✅ 采样测试通过')

print('\n' + '=' * 70)
print('✅ Diffusion Model 实现验证完成!')
print('=' * 70)
print('\n核心组件:')
print('  1. SinusoidalPositionEmbeddings - 正弦位置编码')
print('  2. SimpleUNet - 噪声预测网络')
print('  3. DiffusionModel - 前向/逆向扩散过程')
print('\n训练说明:')
print('  运行: D:\\Anoconda\\envs\\DL\\python.exe diffusion_model.py')
print('  默认在MNIST数据集上训练10轮')
