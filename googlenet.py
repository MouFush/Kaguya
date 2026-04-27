"""
GoogLeNet (Inception v1) 实现
论文: Going Deeper with Convolutions (CVPR 2015)
作者: Christian Szegedy et al.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class InceptionModule(nn.Module):
    """
    Inception模块 - GoogLeNet的核心组件
    包含4个分支:
    1. 1x1卷积
    2. 1x1卷积 + 3x3卷积
    3. 1x1卷积 + 5x5卷积
    4. 3x3最大池化 + 1x1卷积
    """
    def __init__(self, in_channels, ch1x1, ch3x3red, ch3x3, ch5x5red, ch5x5, pool_proj):
        super(InceptionModule, self).__init__()
        
        # 分支1: 1x1卷积
        self.branch1 = nn.Sequential(
            nn.Conv2d(in_channels, ch1x1, kernel_size=1),
            nn.BatchNorm2d(ch1x1),
            nn.ReLU(inplace=True)
        )
        
        # 分支2: 1x1卷积 + 3x3卷积
        self.branch2 = nn.Sequential(
            nn.Conv2d(in_channels, ch3x3red, kernel_size=1),
            nn.BatchNorm2d(ch3x3red),
            nn.ReLU(inplace=True),
            nn.Conv2d(ch3x3red, ch3x3, kernel_size=3, padding=1),
            nn.BatchNorm2d(ch3x3),
            nn.ReLU(inplace=True)
        )
        
        # 分支3: 1x1卷积 + 5x5卷积
        self.branch3 = nn.Sequential(
            nn.Conv2d(in_channels, ch5x5red, kernel_size=1),
            nn.BatchNorm2d(ch5x5red),
            nn.ReLU(inplace=True),
            nn.Conv2d(ch5x5red, ch5x5, kernel_size=5, padding=2),
            nn.BatchNorm2d(ch5x5),
            nn.ReLU(inplace=True)
        )
        
        # 分支4: 3x3最大池化 + 1x1卷积
        self.branch4 = nn.Sequential(
            nn.MaxPool2d(kernel_size=3, stride=1, padding=1),
            nn.Conv2d(in_channels, pool_proj, kernel_size=1),
            nn.BatchNorm2d(pool_proj),
            nn.ReLU(inplace=True)
        )
        
    def forward(self, x):
        branch1 = self.branch1(x)
        branch2 = self.branch2(x)
        branch3 = self.branch3(x)
        branch4 = self.branch4(x)
        
        # 在通道维度上拼接所有分支的输出
        outputs = [branch1, branch2, branch3, branch4]
        return torch.cat(outputs, 1)


class AuxiliaryClassifier(nn.Module):
    """
    辅助分类器 - 用于缓解梯度消失问题
    连接到Inception(4a)和Inception(4d)模块的输出
    """
    def __init__(self, in_channels, num_classes):
        super(AuxiliaryClassifier, self).__init__()
        
        self.avgpool = nn.AdaptiveAvgPool2d((4, 4))
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, 128, kernel_size=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True)
        )
        self.fc1 = nn.Linear(128 * 4 * 4, 1024)
        self.fc2 = nn.Linear(1024, num_classes)
        self.dropout = nn.Dropout(0.7)
        
    def forward(self, x):
        x = self.avgpool(x)
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        x = self.fc1(x)
        x = F.relu(x, inplace=True)
        x = self.dropout(x)
        x = self.fc2(x)
        return x


class GoogLeNet(nn.Module):
    """
    GoogLeNet (Inception v1) 完整网络架构
    
    结构概览:
    - 输入: 224x224x3
    - 卷积层 + 最大池化
    - 9个Inception模块 (分为3组)
    - 2个辅助分类器
    - 全局平均池化 + Dropout + 全连接层
    """
    def __init__(self, num_classes=1000, aux_logits=True, init_weights=True):
        super(GoogLeNet, self).__init__()
        
        self.aux_logits = aux_logits
        
        # 初始卷积层 (stem)
        self.conv1 = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        self.maxpool1 = nn.MaxPool2d(3, stride=2, ceil_mode=True)
        
        self.conv2 = nn.Sequential(
            nn.Conv2d(64, 64, kernel_size=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 192, kernel_size=3, padding=1),
            nn.BatchNorm2d(192),
            nn.ReLU(inplace=True)
        )
        self.maxpool2 = nn.MaxPool2d(3, stride=2, ceil_mode=True)
        
        # Inception模块组1 (3a, 3b)
        self.inception3a = InceptionModule(192, 64, 96, 128, 16, 32, 32)
        self.inception3b = InceptionModule(256, 128, 128, 192, 32, 96, 64)
        self.maxpool3 = nn.MaxPool2d(3, stride=2, ceil_mode=True)
        
        # Inception模块组2 (4a, 4b, 4c, 4d, 4e)
        self.inception4a = InceptionModule(480, 192, 96, 208, 16, 48, 64)
        self.inception4b = InceptionModule(512, 160, 112, 224, 24, 64, 64)
        self.inception4c = InceptionModule(512, 128, 128, 256, 24, 64, 64)
        self.inception4d = InceptionModule(512, 112, 144, 288, 32, 64, 64)
        self.inception4e = InceptionModule(528, 256, 160, 320, 32, 128, 128)
        self.maxpool4 = nn.MaxPool2d(3, stride=2, ceil_mode=True)
        
        # 辅助分类器
        if aux_logits:
            self.aux1 = AuxiliaryClassifier(512, num_classes)
            self.aux2 = AuxiliaryClassifier(528, num_classes)
        else:
            self.aux1 = None
            self.aux2 = None
        
        # Inception模块组3 (5a, 5b)
        self.inception5a = InceptionModule(832, 256, 160, 320, 32, 128, 128)
        self.inception5b = InceptionModule(832, 384, 192, 384, 48, 128, 128)
        
        # 最终分类层
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.dropout = nn.Dropout(0.4)
        self.fc = nn.Linear(1024, num_classes)
        
        if init_weights:
            self._initialize_weights()
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        # 初始卷积层
        x = self.conv1(x)
        x = self.maxpool1(x)
        x = self.conv2(x)
        x = self.maxpool2(x)
        
        # Inception组1
        x = self.inception3a(x)
        x = self.inception3b(x)
        x = self.maxpool3(x)
        
        # Inception组2
        x = self.inception4a(x)
        
        # 辅助分类器1
        if self.aux_logits and self.training:
            aux1 = self.aux1(x)
        else:
            aux1 = None
        
        x = self.inception4b(x)
        x = self.inception4c(x)
        x = self.inception4d(x)
        
        # 辅助分类器2
        if self.aux_logits and self.training:
            aux2 = self.aux2(x)
        else:
            aux2 = None
        
        x = self.inception4e(x)
        x = self.maxpool4(x)
        
        # Inception组3
        x = self.inception5a(x)
        x = self.inception5b(x)
        
        # 最终分类
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.dropout(x)
        x = self.fc(x)
        
        if self.aux_logits and self.training:
            return x, aux1, aux2
        return x


def googlenet(num_classes=1000, pretrained=False, **kwargs):
    """
    创建GoogLeNet模型
    
    Args:
        num_classes: 分类类别数
        pretrained: 是否使用预训练权重
        **kwargs: 其他参数
    """
    model = GoogLeNet(num_classes=num_classes, **kwargs)
    return model


if __name__ == "__main__":
    # 测试网络
    print("=" * 60)
    print("GoogLeNet (Inception v1) 网络结构测试")
    print("=" * 60)
    
    # 创建模型
    model = googlenet(num_classes=1000, aux_logits=True)
    
    # 统计参数量
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    print(f"\n总参数量: {total_params:,}")
    print(f"可训练参数量: {trainable_params:,}")
    
    # 测试前向传播
    print("\n" + "=" * 60)
    print("前向传播测试")
    print("=" * 60)
    
    # 训练模式 (输出主分类 + 2个辅助分类)
    model.train()
    x = torch.randn(2, 3, 224, 224)
    outputs = model(x)
    
    if isinstance(outputs, tuple):
        main_out, aux1_out, aux2_out = outputs
        print(f"训练模式:")
        print(f"  主输出: {main_out.shape}")
        print(f"  辅助分类器1: {aux1_out.shape}")
        print(f"  辅助分类器2: {aux2_out.shape}")
    else:
        print(f"训练模式输出: {outputs.shape}")
    
    # 评估模式 (只输出主分类)
    model.eval()
    with torch.no_grad():
        outputs = model(x)
        print(f"评估模式输出: {outputs.shape}")
    
    # 打印网络结构
    print("\n" + "=" * 60)
    print("网络结构概览")
    print("=" * 60)
    print(model)
    
    print("\n✅ GoogLeNet实现完成!")
