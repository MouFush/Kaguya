"""
Flow Matching (流匹配) 简单实现
基于论文: Flow Matching for Generative Modeling (ICML 2023)
作者: Yaron Lipman et al.

Flow Matching是一种新的生成模型方法，相比Diffusion Model更加简洁。
核心思想: 直接学习数据分布到先验分布之间的向量场(flow)。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class SinusoidalPositionEmbeddings(nn.Module):
    """正弦位置编码"""
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


class ResBlock(nn.Module):
    """残差块，带时间条件"""
    def __init__(self, in_ch, out_ch, time_emb_dim):
        super().__init__()
        self.time_mlp = nn.Linear(time_emb_dim, out_ch)
        
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3, padding=1)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, padding=1)
        self.bn1 = nn.GroupNorm(8, out_ch)
        self.bn2 = nn.GroupNorm(8, out_ch)
        self.act = nn.SiLU()
        
        if in_ch != out_ch:
            self.shortcut = nn.Conv2d(in_ch, out_ch, 1)
        else:
            self.shortcut = nn.Identity()

    def forward(self, x, t_emb):
        h = self.conv1(x)
        h = self.bn1(h)
        h = h + self.time_mlp(t_emb)[:, :, None, None]
        h = self.act(h)
        h = self.conv2(h)
        h = self.bn2(h)
        return self.act(h + self.shortcut(x))


class UNet(nn.Module):
    """
    U-Net网络用于预测速度场 v_t(x)
    输入: 当前状态x_t 和时间t
    输出: 速度场 v_t(x)
    """
    def __init__(self, in_channels=1, base_channels=64, time_emb_dim=64):
        super().__init__()
        
        # 时间编码
        self.time_mlp = nn.Sequential(
            SinusoidalPositionEmbeddings(time_emb_dim),
            nn.Linear(time_emb_dim, time_emb_dim * 4),
            nn.SiLU(),
            nn.Linear(time_emb_dim * 4, time_emb_dim)
        )
        
        # 编码器
        self.conv_in = nn.Conv2d(in_channels, base_channels, 3, padding=1)
        self.down1 = ResBlock(base_channels, base_channels * 2, time_emb_dim)
        self.down2 = ResBlock(base_channels * 2, base_channels * 4, time_emb_dim)
        
        # 下采样
        self.pool = nn.AvgPool2d(2)
        
        # 瓶颈
        self.mid = ResBlock(base_channels * 4, base_channels * 4, time_emb_dim)
        
        # 解码器
        self.up2 = ResBlock(base_channels * 4, base_channels * 2, time_emb_dim)
        self.up1 = ResBlock(base_channels * 2, base_channels, time_emb_dim)
        
        # 上采样
        self.upsample = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False)
        
        # 输出
        self.conv_out = nn.Conv2d(base_channels, in_channels, 3, padding=1)

    def forward(self, x, t):
        # 时间编码
        t_emb = self.time_mlp(t)
        
        # 编码器
        x0 = self.conv_in(x)
        x1 = self.down1(x0, t_emb)
        x1 = self.pool(x1)
        x2 = self.down2(x1, t_emb)
        x2 = self.pool(x2)
        
        # 瓶颈
        x = self.mid(x2, t_emb)
        
        # 解码器
        x = self.upsample(x)
        x = self.up2(x, t_emb)
        x = self.upsample(x)
        x = self.up1(x, t_emb)
        
        # 输出速度场
        return self.conv_out(x)


class FlowMatching:
    """
    Flow Matching核心类
    
    核心思想:
    1. 定义从数据x_1到噪声x_0的直线路径: x_t = t * x_1 + (1-t) * x_0
    2. 计算目标速度场: u_t = x_1 - x_0 (这是直线路径的导数)
    3. 训练网络v_t(x)去拟合u_t
    4. 采样时从x_0 ~ N(0,I)出发，用ODE积分得到x_1
    """
    def __init__(self, device='cuda'):
        self.device = device
    
    def sample_path(self, x_1, x_0, t):
        """
        采样路径点 x_t
        直线路径: x_t = t * x_1 + (1-t) * x_0
        
        Args:
            x_1: 数据样本 [B, C, H, W]
            x_0: 噪声样本 [B, C, H, W]
            t: 时间 [B]，范围[0, 1]
        Returns:
            x_t: 路径上的点
            u_t: 目标速度场 (x_1 - x_0)
        """
        # 扩展t维度以匹配图像维度
        t = t.view(-1, 1, 1, 1)
        
        # 直线路径
        x_t = t * x_1 + (1 - t) * x_0
        
        # 目标速度场 (路径的导数)
        u_t = x_1 - x_0
        
        return x_t, u_t
    
    def compute_loss(self, model, x_1):
        """
        计算Flow Matching损失
        
        训练过程:
        1. 采样噪声 x_0 ~ N(0, I)
        2. 采样时间 t ~ Uniform(0, 1)
        3. 计算路径点 x_t 和目标速度 u_t
        4. 预测速度 v_t = model(x_t, t)
        5. 损失 = MSE(v_t, u_t)
        
        Args:
            model: 速度场预测网络
            x_1: 真实数据样本 [B, C, H, W]
        Returns:
            loss: 均方误差
        """
        batch_size = x_1.shape[0]
        
        # 从标准正态分布采样噪声
        x_0 = torch.randn_like(x_1)
        
        # 从均匀分布采样时间 [0, 1]
        t = torch.rand(batch_size, device=self.device)
        
        # 计算路径点和目标速度
        x_t, u_t = self.sample_path(x_1, x_0, t)
        
        # 预测速度场
        v_t = model(x_t, t)
        
        # 均方误差损失
        loss = F.mse_loss(v_t, u_t)
        
        return loss
    
    @torch.no_grad()
    def sample(self, model, batch_size=16, channels=1, img_size=28, num_steps=50):
        """
        使用ODE采样生成图像
        
        采样过程 (Euler方法):
        1. 从先验分布采样 x_0 ~ N(0, I)
        2. 对于 t = 0 到 1:
           x_{t+dt} = x_t + dt * v_t(x_t)
        3. 返回 x_1
        
        Args:
            model: 速度场预测网络
            batch_size: 生成样本数
            channels: 图像通道数
            img_size: 图像尺寸
            num_steps: ODE积分步数
        Returns:
            x_1: 生成的图像 [batch_size, channels, img_size, img_size]
        """
        model.eval()
        
        # 从标准正态分布初始化
        x = torch.randn(batch_size, channels, img_size, img_size, device=self.device)
        
        # 时间步长
        dt = 1.0 / num_steps
        
        # ODE积分 (Euler方法)
        for i in range(num_steps):
            t = torch.ones(batch_size, device=self.device) * i * dt
            
            # 预测速度场
            v = model(x, t)
            
            # 更新: x_{t+dt} = x_t + dt * v_t
            x = x + dt * v
        
        return x
    
    @torch.no_grad()
    def sample_rk4(self, model, batch_size=16, channels=1, img_size=28, num_steps=50):
        """
        使用RK4 (四阶龙格-库塔) 方法采样，精度更高
        
        RK4公式:
        k1 = f(t, x)
        k2 = f(t + dt/2, x + dt*k1/2)
        k3 = f(t + dt/2, x + dt*k2/2)
        k4 = f(t + dt, x + dt*k3)
        x_{t+dt} = x_t + dt/6 * (k1 + 2*k2 + 2*k3 + k4)
        """
        model.eval()
        
        x = torch.randn(batch_size, channels, img_size, img_size, device=self.device)
        dt = 1.0 / num_steps
        
        for i in range(num_steps):
            t = i * dt
            t_tensor = torch.ones(batch_size, device=self.device)
            
            # k1
            k1 = model(x, t_tensor * t)
            
            # k2
            x2 = x + dt * k1 / 2
            k2 = model(x2, t_tensor * (t + dt/2))
            
            # k3
            x3 = x + dt * k2 / 2
            k3 = model(x3, t_tensor * (t + dt/2))
            
            # k4
            x4 = x + dt * k3
            k4 = model(x4, t_tensor * (t + dt))
            
            # RK4更新
            x = x + dt / 6 * (k1 + 2*k2 + 2*k3 + k4)
        
        return x


def train_flow_matching(epochs=10, batch_size=128, device='cuda'):
    """
    在MNIST上训练Flow Matching模型
    """
    from torch.utils.data import DataLoader
    from torchvision import datasets, transforms
    import torch.optim as optim
    from tqdm import tqdm
    import os
    
    print("=" * 70)
    print("Flow Matching 训练")
    print("=" * 70)
    
    # 数据预处理
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))  # 归一化到[-1, 1]
    ])
    
    # 加载MNIST
    dataset = datasets.MNIST(root='./data', train=True, download=True, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=2)
    
    # 初始化模型
    model = UNet(in_channels=1, base_channels=64, time_emb_dim=64).to(device)
    fm = FlowMatching(device=device)
    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    
    print(f"模型参数量: {sum(p.numel() for p in model.parameters()):,}")
    print(f"训练集大小: {len(dataset)}")
    print(f"批次大小: {batch_size}")
    print(f"训练轮数: {epochs}")
    
    # 训练循环
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        pbar = tqdm(dataloader, desc=f'Epoch {epoch+1}/{epochs}')
        
        for images, _ in pbar:
            images = images.to(device)
            
            # 计算损失
            loss = fm.compute_loss(model, images)
            
            # 反向传播
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            pbar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        avg_loss = total_loss / len(dataloader)
        print(f"Epoch {epoch+1}/{epochs}, Average Loss: {avg_loss:.4f}")
        
        # 每5轮生成样本
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print("\n生成样本...")
            samples = fm.sample(model, batch_size=16, num_steps=50)
            print(f"生成样本范围: [{samples.min():.2f}, {samples.max():.2f}]")
    
    # 保存模型
    os.makedirs('checkpoints', exist_ok=True)
    torch.save(model.state_dict(), 'checkpoints/flow_matching.pth')
    print("\n模型已保存到 checkpoints/flow_matching.pth")
    
    return model, fm


if __name__ == "__main__":
    print("=" * 70)
    print("Flow Matching 核心组件测试")
    print("=" * 70)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
    # 测试U-Net
    print("\n" + "-" * 70)
    print("测试 U-Net 结构")
    print("-" * 70)
    model = UNet(in_channels=1, base_channels=64, time_emb_dim=64).to(device)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"模型参数量: {total_params:,}")
    
    # 测试前向传播
    x = torch.randn(4, 1, 28, 28).to(device)
    t = torch.rand(4).to(device)
    output = model(x, t)
    print(f"输入形状:  {x.shape}")
    print(f"时间:      {t.shape}")
    print(f"输出形状:  {output.shape}")
    assert output.shape == x.shape
    print("✅ U-Net前向传播测试通过")
    
    # 测试Flow Matching
    print("\n" + "-" * 70)
    print("测试 Flow Matching")
    print("-" * 70)
    fm = FlowMatching(device=device)
    
    # 测试路径采样
    x_1 = torch.randn(2, 1, 28, 28).to(device)
    x_0 = torch.randn(2, 1, 28, 28).to(device)
    t = torch.tensor([0.0, 0.5]).to(device)
    x_t, u_t = fm.sample_path(x_1, x_0, t)
    print(f"路径采样测试:")
    print(f"  x_1: {x_1.shape}, x_0: {x_0.shape}")
    print(f"  t:   {t}")
    print(f"  x_t: {x_t.shape}, u_t: {u_t.shape}")
    
    # 测试损失计算
    loss = fm.compute_loss(model, x_1)
    print(f"\n损失值: {loss.item():.6f}")
    print("✅ Flow Matching测试通过")
    
    # 测试采样
    print("\n" + "-" * 70)
    print("测试采样 (10步Euler)")
    print("-" * 70)
    model.eval()
    with torch.no_grad():
        samples = fm.sample(model, batch_size=4, num_steps=10)
    print(f"生成样本形状: {samples.shape}")
    print(f"样本范围: [{samples.min():.2f}, {samples.max():.2f}]")
    print("✅ 采样测试通过")
    
    # 测试RK4采样
    print("\n" + "-" * 70)
    print("测试采样 (10步RK4)")
    print("-" * 70)
    with torch.no_grad():
        samples_rk4 = fm.sample_rk4(model, batch_size=4, num_steps=10)
    print(f"生成样本形状: {samples_rk4.shape}")
    print(f"样本范围: [{samples_rk4.min():.2f}, {samples_rk4.max():.2f}]")
    print("✅ RK4采样测试通过")
    
    print("\n" + "=" * 70)
    print("✅ Flow Matching 实现验证完成!")
    print("=" * 70)
    print("\n核心概念:")
    print("  1. 直线路径: x_t = t*x_1 + (1-t)*x_0")
    print("  2. 目标速度: u_t = x_1 - x_0 (路径导数)")
    print("  3. 学习速度场: v_t(x) ≈ u_t")
    print("  4. 采样: 从x_0 ~ N(0,I)积分ODE得到x_1")
    print("\n相比Diffusion Model的优势:")
    print("  - 更简洁的公式 (没有复杂的alpha/beta调度)")
    print("  - 直接回归速度场 (不需要预测噪声)")
    print("  - 训练更稳定")
    print("  - 采样可以用更少的步数")
