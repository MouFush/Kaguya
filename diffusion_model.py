"""
简单Diffusion Model (扩散模型) 实现
基于DDPM (Denoising Diffusion Probabilistic Models)
论文: Denoising Diffusion Probabilistic Models (NeurIPS 2020)
作者: Jonathan Ho et al.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os


class SinusoidalPositionEmbeddings(nn.Module):
    """
    正弦位置编码 - 将时间步t编码为向量
    使用正弦和余弦函数的不同频率
    """
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, time):
        device = time.device
        half_dim = self.dim // 2
        embeddings = np.log(10000) / (half_dim - 1)
        embeddings = torch.exp(torch.arange(half_dim, device=device) * -embeddings)
        embeddings = time[:, None] * embeddings[None, :]
        embeddings = torch.cat((embeddings.sin(), embeddings.cos()), dim=-1)
        return embeddings


class Block(nn.Module):
    """
    基础卷积块 - 包含卷积、归一化和激活
    """
    def __init__(self, in_ch, out_ch, time_emb_dim, up=False):
        super().__init__()
        self.time_mlp = nn.Linear(time_emb_dim, out_ch)
        
        if up:
            self.conv1 = nn.Conv2d(2*in_ch, out_ch, 3, padding=1)
            self.transform = nn.ConvTranspose2d(out_ch, out_ch, 4, 2, 1)
        else:
            self.conv1 = nn.Conv2d(in_ch, out_ch, 3, padding=1)
            self.transform = nn.Conv2d(out_ch, out_ch, 4, 2, 1)
        
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(out_ch)
        self.bn2 = nn.BatchNorm2d(out_ch)
        self.relu = nn.ReLU()

    def forward(self, x, t):
        # 时间嵌入
        t_emb = self.time_mlp(t)
        t_emb = t_emb[:, :, None, None].expand(-1, -1, x.shape[-2], x.shape[-1])
        
        # 第一个卷积
        h = self.bn1(self.conv1(x))
        h = h + t_emb  # 添加时间信息
        h = self.relu(h)
        
        # 第二个卷积
        h = self.bn2(self.conv2(h))
        h = self.relu(h)
        
        # 上采样或下采样
        return self.transform(h)


class SimpleUNet(nn.Module):
    """
    简化的U-Net网络 - 用于预测噪声
    结构: 编码器 -> 瓶颈 -> 解码器，带跳跃连接
    """
    def __init__(self, in_channels=1, time_emb_dim=32):
        super().__init__()
        
        # 时间编码
        self.time_mlp = nn.Sequential(
            SinusoidalPositionEmbeddings(time_emb_dim),
            nn.Linear(time_emb_dim, time_emb_dim),
            nn.ReLU()
        )
        
        # 编码器 (下采样)
        self.conv0 = nn.Conv2d(in_channels, 64, 3, padding=1)
        self.down1 = Block(64, 128, time_emb_dim)
        self.down2 = Block(128, 256, time_emb_dim)
        
        # 瓶颈
        self.bottleneck = nn.Sequential(
            nn.Conv2d(256, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU()
        )
        
        # 解码器 (上采样)
        self.up2 = Block(256, 128, time_emb_dim, up=True)
        self.up1 = Block(128, 64, time_emb_dim, up=True)
        
        # 输出层
        self.conv_out = nn.Conv2d(64, in_channels, 1)

    def forward(self, x, timestep):
        # 时间编码
        t = self.time_mlp(timestep)
        
        # 编码器
        x0 = self.conv0(x)
        x1 = self.down1(x0, t)
        x2 = self.down2(x1, t)
        
        # 瓶颈
        x2 = self.bottleneck(x2)
        
        # 解码器 (带跳跃连接)
        x = self.up2(x2, t)
        x = self.up1(x, t)
        
        # 输出预测的噪声
        return self.conv_out(x)


class DiffusionModel:
    """
    扩散模型核心类
    实现前向加噪过程和逆向去噪过程
    """
    def __init__(self, timesteps=1000, beta_start=1e-4, beta_end=0.02, device='cuda'):
        self.timesteps = timesteps
        self.device = device
        
        # 定义beta调度 (线性调度)
        self.betas = torch.linspace(beta_start, beta_end, timesteps).to(device)
        
        # 计算alpha
        self.alphas = 1.0 - self.betas
        self.alphas_cumprod = torch.cumprod(self.alphas, dim=0)
        self.alphas_cumprod_prev = F.pad(self.alphas_cumprod[:-1], (1, 0), value=1.0)
        
        # 预计算一些值用于加速
        self.sqrt_alphas_cumprod = torch.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = torch.sqrt(1.0 - self.alphas_cumprod)
        
        # 用于采样的值
        self.sqrt_recip_alphas = torch.sqrt(1.0 / self.alphas)
        self.posterior_variance = self.betas * (1.0 - self.alphas_cumprod_prev) / (1.0 - self.alphas_cumprod)
    
    def q_sample(self, x_start, t, noise=None):
        """
        前向扩散过程: 根据时间步t添加噪声
        q(x_t | x_0) = sqrt(alpha_cumprod) * x_0 + sqrt(1 - alpha_cumprod) * noise
        
        Args:
            x_start: 原始图像 [B, C, H, W]
            t: 时间步 [B]
            noise: 可选的噪声，如果不提供则随机采样
        Returns:
            x_t: 加噪后的图像
            noise: 添加的噪声
        """
        if noise is None:
            noise = torch.randn_like(x_start)
        
        # 获取对应时间步的系数
        sqrt_alphas_cumprod_t = self._extract(self.sqrt_alphas_cumprod, t, x_start.shape)
        sqrt_one_minus_alphas_cumprod_t = self._extract(self.sqrt_one_minus_alphas_cumprod, t, x_start.shape)
        
        # 加噪公式
        x_t = sqrt_alphas_cumprod_t * x_start + sqrt_one_minus_alphas_cumprod_t * noise
        
        return x_t, noise
    
    def _extract(self, a, t, x_shape):
        """从张量a中提取对应时间步t的值"""
        batch_size = t.shape[0]
        out = a.gather(-1, t)
        return out.reshape(batch_size, *((1,) * (len(x_shape) - 1)))
    
    def p_losses(self, denoise_model, x_start, t, noise=None):
        """
        计算训练损失 - 预测噪声
        
        Args:
            denoise_model: 噪声预测网络
            x_start: 原始图像
            t: 时间步
            noise: 可选的噪声
        Returns:
            loss: MSE损失
        """
        if noise is None:
            noise = torch.randn_like(x_start)
        
        # 加噪
        x_t, noise = self.q_sample(x_start, t, noise)
        
        # 预测噪声
        predicted_noise = denoise_model(x_t, t)
        
        # MSE损失
        loss = F.mse_loss(noise, predicted_noise)
        
        return loss
    
    @torch.no_grad()
    def p_sample(self, denoise_model, x_t, t):
        """
        逆向去噪单步: 从x_t采样x_{t-1}
        
        Args:
            denoise_model: 噪声预测网络
            x_t: 当前时刻的噪声图像
            t: 时间步
        Returns:
            x_{t-1}: 去噪后的图像
        """
        # 预测噪声
        predicted_noise = denoise_model(x_t, t)
        
        # 提取系数
        betas_t = self._extract(self.betas, t, x_t.shape)
        sqrt_one_minus_alphas_cumprod_t = self._extract(self.sqrt_one_minus_alphas_cumprod, t, x_t.shape)
        sqrt_recip_alphas_t = self._extract(self.sqrt_recip_alphas, t, x_t.shape)
        
        # 计算均值
        model_mean = sqrt_recip_alphas_t * (x_t - betas_t * predicted_noise / sqrt_one_minus_alphas_cumprod_t)
        
        # 只在t>0时添加噪声
        if t[0] == 0:
            return model_mean
        else:
            posterior_variance_t = self._extract(self.posterior_variance, t, x_t.shape)
            noise = torch.randn_like(x_t)
            return model_mean + torch.sqrt(posterior_variance_t) * noise
    
    @torch.no_grad()
    def sample(self, denoise_model, batch_size=16, channels=1, img_size=28):
        """
        完整的采样过程 - 从纯噪声生成图像
        
        Args:
            denoise_model: 噪声预测网络
            batch_size: 生成图像数量
            channels: 图像通道数
            img_size: 图像尺寸
        Returns:
            生成的图像 [batch_size, channels, img_size, img_size]
        """
        denoise_model.eval()
        
        # 从纯噪声开始
        shape = (batch_size, channels, img_size, img_size)
        img = torch.randn(shape, device=self.device)
        
        # 逐步去噪
        for i in tqdm(reversed(range(self.timesteps)), desc='Sampling', total=self.timesteps):
            t = torch.full((batch_size,), i, device=self.device, dtype=torch.long)
            img = self.p_sample(denoise_model, img, t)
        
        return img


def train_diffusion_model(epochs=10, batch_size=128, timesteps=1000, device='cuda'):
    """
    训练扩散模型
    """
    print("=" * 70)
    print("Diffusion Model 训练")
    print("=" * 70)
    
    # 数据预处理
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))  # 归一化到[-1, 1]
    ])
    
    # 加载MNIST数据集
    dataset = datasets.MNIST(root='./data', train=True, download=True, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=2)
    
    # 初始化模型
    model = SimpleUNet(in_channels=1, time_emb_dim=32).to(device)
    diffusion = DiffusionModel(timesteps=timesteps, device=device)
    optimizer = optim.Adam(model.parameters(), lr=2e-4)
    
    print(f"模型参数量: {sum(p.numel() for p in model.parameters()):,}")
    print(f"训练集大小: {len(dataset)}")
    print(f"批次大小: {batch_size}")
    print(f"时间步数: {timesteps}")
    print(f"训练轮数: {epochs}")
    
    # 训练循环
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        pbar = tqdm(dataloader, desc=f'Epoch {epoch+1}/{epochs}')
        
        for batch_idx, (images, _) in enumerate(pbar):
            images = images.to(device)
            batch_size = images.shape[0]
            
            # 随机采样时间步
            t = torch.randint(0, timesteps, (batch_size,), device=device).long()
            
            # 计算损失
            loss = diffusion.p_losses(model, images, t)
            
            # 反向传播
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            pbar.set_postfix({'loss': loss.item()})
        
        avg_loss = total_loss / len(dataloader)
        print(f"Epoch {epoch+1}/{epochs}, Average Loss: {avg_loss:.4f}")
        
        # 每5轮保存一次生成的样本
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"\n生成样本...")
            samples = diffusion.sample(model, batch_size=16, channels=1, img_size=28)
            save_samples(samples, epoch + 1)
    
    # 保存模型
    os.makedirs('checkpoints', exist_ok=True)
    torch.save(model.state_dict(), 'checkpoints/diffusion_model.pth')
    print("\n模型已保存到 checkpoints/diffusion_model.pth")
    
    return model, diffusion


def save_samples(samples, epoch, save_dir='samples'):
    """保存生成的样本"""
    os.makedirs(save_dir, exist_ok=True)
    
    # 反归一化到[0, 1]
    samples = (samples + 1) / 2
    samples = samples.clamp(0, 1)
    
    # 创建图像网格
    fig, axes = plt.subplots(4, 4, figsize=(8, 8))
    for i, ax in enumerate(axes.flat):
        ax.imshow(samples[i, 0].cpu().numpy(), cmap='gray')
        ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(f'{save_dir}/samples_epoch_{epoch}.png')
    plt.close()
    print(f"样本已保存到 {save_dir}/samples_epoch_{epoch}.png")


def generate_samples(model, diffusion, num_samples=16, device='cuda'):
    """使用训练好的模型生成样本"""
    print("\n生成样本...")
    model.eval()
    samples = diffusion.sample(model, batch_size=num_samples, channels=1, img_size=28)
    save_samples(samples, 'final')
    return samples


def visualize_forward_process(diffusion, dataloader, device='cuda'):
    """可视化前向扩散过程"""
    print("\n可视化前向扩散过程...")
    
    # 获取一张图像
    images, _ = next(iter(dataloader))
    x_start = images[0:1].to(device)
    
    # 不同时间步的加噪结果
    timesteps_to_show = [0, 100, 300, 500, 700, 999]
    fig, axes = plt.subplots(1, len(timesteps_to_show), figsize=(15, 3))
    
    for i, t_val in enumerate(timesteps_to_show):
        t = torch.tensor([t_val], device=device)
        x_t, _ = diffusion.q_sample(x_start, t)
        
        # 反归一化
        img = (x_t[0, 0].cpu().numpy() + 1) / 2
        img = np.clip(img, 0, 1)
        
        axes[i].imshow(img, cmap='gray')
        axes[i].set_title(f't={t_val}')
        axes[i].axis('off')
    
    plt.tight_layout()
    os.makedirs('samples', exist_ok=True)
    plt.savefig('samples/forward_process.png')
    plt.close()
    print("前向扩散过程已保存到 samples/forward_process.png")


if __name__ == "__main__":
    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
    # 参数设置
    EPOCHS = 10  # 训练轮数
    BATCH_SIZE = 128
    TIMESTEPS = 1000
    
    # 检查是否有预训练模型
    model_path = 'checkpoints/diffusion_model.pth'
    
    if os.path.exists(model_path):
        print("\n加载预训练模型...")
        model = SimpleUNet(in_channels=1, time_emb_dim=32).to(device)
        model.load_state_dict(torch.load(model_path))
        diffusion = DiffusionModel(timesteps=TIMESTEPS, device=device)
        
        # 生成样本
        generate_samples(model, diffusion, num_samples=16, device=device)
    else:
        print("\n开始训练...")
        model, diffusion = train_diffusion_model(
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            timesteps=TIMESTEPS,
            device=device
        )
        
        # 最终生成
        generate_samples(model, diffusion, num_samples=16, device=device)
    
    # 可视化前向过程
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])
    dataset = datasets.MNIST(root='./data', train=True, download=True, transform=transform)
    dataloader = DataLoader(dataset, batch_size=16, shuffle=True)
    visualize_forward_process(diffusion, dataloader, device)
    
    print("\n✅ Diffusion Model 完成!")
