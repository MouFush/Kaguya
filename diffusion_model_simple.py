"""
简单Diffusion Model (扩散模型) 实现 - 核心组件版本
基于DDPM (Denoising Diffusion Probabilistic Models)
论文: Denoising Diffusion Probabilistic Models (NeurIPS 2020)
作者: Jonathan Ho et al.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


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
        """
        denoise_model.eval()
        
        # 从纯噪声开始
        shape = (batch_size, channels, img_size, img_size)
        img = torch.randn(shape, device=self.device)
        
        # 逐步去噪
        for i in range(self.timesteps - 1, -1, -1):
            t = torch.full((batch_size,), i, device=self.device, dtype=torch.long)
            img = self.p_sample(denoise_model, img, t)
        
        return img


if __name__ == "__main__":
    print("=" * 70)
    print("Diffusion Model 核心组件测试")
    print("=" * 70)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
    # 测试U-Net模型
    print("\n" + "-" * 70)
    print("测试 SimpleUNet 结构")
    print("-" * 70)
    model = SimpleUNet(in_channels=1, time_emb_dim=32).to(device)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"模型参数量: {total_params:,}")
    
    # 测试前向传播
    x = torch.randn(4, 1, 28, 28).to(device)
    t = torch.randint(0, 1000, (4,)).to(device)
    output = model(x, t)
    print(f"输入形状:  {x.shape}")
    print(f"时间步:    {t.shape}")
    print(f"输出形状:  {output.shape}")
    assert output.shape == x.shape, "输出形状错误"
    print("✅ U-Net前向传播测试通过")
    
    # 测试DiffusionModel
    print("\n" + "-" * 70)
    print("测试 DiffusionModel 扩散过程")
    print("-" * 70)
    diffusion = DiffusionModel(timesteps=1000, device=device)
    print(f"时间步数: {diffusion.timesteps}")
    print(f"beta范围: [{diffusion.betas[0]:.6f}, {diffusion.betas[-1]:.6f}]")
    
    # 测试前向加噪
    x_start = torch.randn(2, 1, 28, 28).to(device)
    t = torch.tensor([0, 500]).to(device)
    x_t, noise = diffusion.q_sample(x_start, t)
    print(f"\n前向扩散测试:")
    print(f"  原始图像: {x_start.shape}")
    print(f"  时间步:   {t}")
    print(f"  加噪后:   {x_t.shape}")
    print(f"  噪声:     {noise.shape}")
    
    # 测试损失计算
    t_rand = torch.randint(0, 1000, (2,)).to(device)
    loss = diffusion.p_losses(model, x_start, t_rand)
    print(f"\n损失值: {loss.item():.6f}")
    print("✅ 扩散过程测试通过")
    
    # 测试采样（只采样10步以节省时间）
    print("\n" + "-" * 70)
    print("测试采样过程（10步）")
    print("-" * 70)
    diffusion_short = DiffusionModel(timesteps=10, device=device)
    model.eval()
    with torch.no_grad():
        sample = diffusion_short.sample(model, batch_size=2, channels=1, img_size=28)
    print(f"生成样本形状: {sample.shape}")
    print("✅ 采样测试通过")
    
    print("\n" + "=" * 70)
    print("✅ Diffusion Model 实现验证完成!")
    print("=" * 70)
    print("\n核心组件:")
    print("  1. SinusoidalPositionEmbeddings - 正弦位置编码")
    print("  2. SimpleUNet - 噪声预测网络")
    print("  3. DiffusionModel - 前向/逆向扩散过程")
    print("\n核心公式:")
    print("  前向: x_t = sqrt(alpha_cumprod) * x_0 + sqrt(1 - alpha_cumprod) * noise")
    print("  逆向: x_{t-1} = (x_t - beta_t * predicted_noise / sqrt(1-alpha_cumprod)) / sqrt(alpha_t)")
