"""
ResNet (Residual Network) 实现
论文: Deep Residual Learning for Image Recognition (CVPR 2016)
作者: Kaiming He et al.
"""

import torch
import torch.nn as nn


class BasicBlock(nn.Module):
    """
    基础残差块 - 用于ResNet-18/34
    结构: Conv3x3 → BN → ReLU → Conv3x3 → BN → (+shortcut) → ReLU
    """
    expansion = 1  # 输出通道数相对于输入通道数的倍数
    
    def __init__(self, in_channels, out_channels, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        
        # 第一个卷积层，可能下采样
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, 
                               stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        
        # 第二个卷积层，不下采样
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3,
                               stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        self.downsample = downsample  # shortcut连接的下采样层
        self.relu = nn.ReLU(inplace=True)
        
    def forward(self, x):
        identity = x  # 保存输入用于残差连接
        
        # 主路径
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        
        out = self.conv2(out)
        out = self.bn2(out)
        
        # shortcut连接
        if self.downsample is not None:
            identity = self.downsample(x)
        
        # 残差连接
        out += identity
        out = self.relu(out)
        
        return out


class Bottleneck(nn.Module):
    """
    瓶颈残差块 - 用于ResNet-50/101/152
    结构: Conv1x1 → BN → ReLU → Conv3x3 → BN → ReLU → Conv1x1 → BN → (+shortcut) → ReLU
    
    相比BasicBlock，使用1x1卷积先降维再升维，减少计算量
    """
    expansion = 4  # 输出通道数是输入通道数的4倍
    
    def __init__(self, in_channels, out_channels, stride=1, downsample=None):
        super(Bottleneck, self).__init__()
        
        # 1x1卷积降维
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        
        # 3x3卷积提取特征
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3,
                               stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        # 1x1卷积升维
        self.conv3 = nn.Conv2d(out_channels, out_channels * self.expansion,
                               kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(out_channels * self.expansion)
        
        self.downsample = downsample
        self.relu = nn.ReLU(inplace=True)
        
    def forward(self, x):
        identity = x
        
        # 主路径
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        
        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)
        
        out = self.conv3(out)
        out = self.bn3(out)
        
        # shortcut连接
        if self.downsample is not None:
            identity = self.downsample(x)
        
        # 残差连接
        out += identity
        out = self.relu(out)
        
        return out


class ResNet(nn.Module):
    """
    ResNet网络架构
    
    结构概览:
    - 输入: 224x224x3
    - Conv7x7 + MaxPool
    - 4个残差层 (layer1-4)，每层包含多个残差块
    - 全局平均池化 + 全连接层
    
    不同版本的区别在于残差块类型和每层残差块数量:
    - ResNet-18: BasicBlock, [2, 2, 2, 2]
    - ResNet-34: BasicBlock, [3, 4, 6, 3]
    - ResNet-50: Bottleneck, [3, 4, 6, 3]
    - ResNet-101: Bottleneck, [3, 4, 23, 3]
    - ResNet-152: Bottleneck, [3, 8, 36, 3]
    """
    
    def __init__(self, block, layers, num_classes=1000, zero_init_residual=False):
        super(ResNet, self).__init__()
        
        self.in_channels = 64  # 当前通道数，用于构建残差层
        
        # 初始卷积层 (stem)
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        
        # 4个残差层
        self.layer1 = self._make_layer(block, 64, layers[0])      # 输出: 64*expansion
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)  # 输出: 128*expansion
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2)  # 输出: 256*expansion
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2)  # 输出: 512*expansion
        
        # 最终分类层
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512 * block.expansion, num_classes)
        
        # 权重初始化
        self._initialize_weights()
        
        # 可选：零初始化残差分支最后的BN层，使网络初始表现为恒等映射
        if zero_init_residual:
            self._zero_init_residual()
    
    def _make_layer(self, block, out_channels, num_blocks, stride=1):
        """
        构建一个残差层
        
        Args:
            block: 残差块类型 (BasicBlock 或 Bottleneck)
            out_channels: 输出通道数
            num_blocks: 残差块数量
            stride: 第一个残差块的步长
        """
        downsample = None
        
        # 当stride不为1或输入输出通道数不匹配时，需要下采样shortcut
        if stride != 1 or self.in_channels != out_channels * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.in_channels, out_channels * block.expansion,
                         kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels * block.expansion)
            )
        
        layers = []
        # 第一个残差块，可能需要下采样
        layers.append(block(self.in_channels, out_channels, stride, downsample))
        
        # 更新当前通道数
        self.in_channels = out_channels * block.expansion
        
        # 后续残差块，不下采样
        for _ in range(1, num_blocks):
            layers.append(block(self.in_channels, out_channels))
        
        return nn.Sequential(*layers)
    
    def _initialize_weights(self):
        """He初始化"""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)
    
    def _zero_init_residual(self):
        """零初始化残差分支最后的BN层"""
        for m in self.modules():
            if isinstance(m, Bottleneck):
                nn.init.constant_(m.bn3.weight, 0)
            elif isinstance(m, BasicBlock):
                nn.init.constant_(m.bn2.weight, 0)
    
    def forward(self, x):
        # 初始卷积层
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        # 4个残差层
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        
        # 最终分类层
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        
        return x


def resnet18(num_classes=1000, **kwargs):
    """ResNet-18: BasicBlock, [2,2,2,2], 约1168万参数"""
    return ResNet(BasicBlock, [2, 2, 2, 2], num_classes=num_classes, **kwargs)


def resnet34(num_classes=1000, **kwargs):
    """ResNet-34: BasicBlock, [3,4,6,3], 约2179万参数"""
    return ResNet(BasicBlock, [3, 4, 6, 3], num_classes=num_classes, **kwargs)


def resnet50(num_classes=1000, **kwargs):
    """ResNet-50: Bottleneck, [3,4,6,3], 约2556万参数"""
    return ResNet(Bottleneck, [3, 4, 6, 3], num_classes=num_classes, **kwargs)


def resnet101(num_classes=1000, **kwargs):
    """ResNet-101: Bottleneck, [3,4,23,3], 约4455万参数"""
    return ResNet(Bottleneck, [3, 4, 23, 3], num_classes=num_classes, **kwargs)


def resnet152(num_classes=1000, **kwargs):
    """ResNet-152: Bottleneck, [3,8,36,3], 约6019万参数"""
    return ResNet(Bottleneck, [3, 8, 36, 3], num_classes=num_classes, **kwargs)


if __name__ == "__main__":
    print("=" * 70)
    print("ResNet 网络结构测试")
    print("论文: Deep Residual Learning for Image Recognition (CVPR 2016)")
    print("=" * 70)
    
    # 测试不同版本的ResNet
    models_config = [
        ('ResNet-18', resnet18),
        ('ResNet-34', resnet34),
        ('ResNet-50', resnet50),
        ('ResNet-101', resnet101),
        ('ResNet-152', resnet152)
    ]
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n使用设备: {device}")
    
    for name, model_fn in models_config:
        print("\n" + "-" * 70)
        print(f"测试 {name}")
        print("-" * 70)
        
        # 创建模型
        model = model_fn(num_classes=1000)
        model = model.to(device)
        model.eval()
        
        # 统计参数量
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        print(f"总参数量: {total_params:,}")
        print(f"可训练参数量: {trainable_params:,}")
        
        # 测试前向传播
        x = torch.randn(2, 3, 224, 224).to(device)
        with torch.no_grad():
            output = model(x)
        
        print(f"输入形状: {x.shape}")
        print(f"输出形状: {output.shape}")
        
        # 验证输出维度
        assert output.shape == (2, 1000), f"输出形状错误: {output.shape}"
        print("✅ 前向传播测试通过")
    
    # 详细展示ResNet-50结构
    print("\n" + "=" * 70)
    print("ResNet-50 详细网络结构")
    print("=" * 70)
    model = resnet50(num_classes=1000)
    print(model)
    
    # 展示残差连接原理
    print("\n" + "=" * 70)
    print("残差连接可视化说明")
    print("=" * 70)
    print("""
    输入 x
      │
      ├──→ [Conv1x1] → [BN] → [ReLU] → [Conv3x3] → [BN] → [ReLU] → [Conv1x1] → [BN]
      │                                                            │
      └────────────────────────────────────────────────────────────┘
                                                                   ↓
                                                                [ReLU]
                                                                   ↓
                                                                输出
    
    数学表达: output = F(x) + x
    其中 F(x) 是残差映射，x 是shortcut连接
    """)
    
    print("\n✅ ResNet实现完成!")
