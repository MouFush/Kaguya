import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

# 设置随机种子以确保结果可重复
np.random.seed(42)
torch.manual_seed(42)

# 准备示例数据
# 生成简单的序列数据：输入是0-9的数字，目标是预测下一个数字
def create_dataset(sequence_length, num_samples):
    X = []
    y = []
    for _ in range(num_samples):
        # 生成一个随机起始点
        start = np.random.randint(0, 10 - sequence_length)
        # 创建序列
        sequence = np.arange(start, start + sequence_length)
        # 下一个数字作为目标
        target = start + sequence_length
        # 归一化输入到0-1范围
        X.append(sequence / 10.0)
        y.append(target)
    return np.array(X), np.array(y)

# 自定义数据集类
class SequenceDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32).unsqueeze(-1)  # 添加特征维度
        self.y = torch.tensor(y, dtype=torch.long)
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

# LSTM模型类
class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)
    
    def forward(self, x):
        # 前向传播
        out, _ = self.lstm(x)
        # 取最后一个时间步的输出
        out = out[:, -1, :]
        out = self.fc(out)
        return out

# 超参数
sequence_length = 3  # 输入序列长度
num_samples = 1000    # 样本数量
num_epochs = 50       # 训练轮数
batch_size = 32       # 批次大小
input_size = 1         # 输入特征维度
hidden_size = 32       # LSTM隐藏层大小
num_classes = 10       # 输出类别数

# 创建数据集
X, y = create_dataset(sequence_length, num_samples)

# 分割数据集为训练集和测试集
split_idx = int(0.8 * num_samples)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

# 创建数据加载器
train_dataset = SequenceDataset(X_train, y_train)
test_dataset = SequenceDataset(X_test, y_test)
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

# 创建模型
model = LSTMModel(input_size, hidden_size, num_classes)
print(model)

# 定义损失函数和优化器
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 训练模型
print("\n开始训练...")
for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for inputs, targets in train_loader:
        # 清零梯度
        optimizer.zero_grad()
        # 前向传播
        outputs = model(inputs)
        # 计算损失
        loss = criterion(outputs, targets)
        # 反向传播
        loss.backward()
        # 更新参数
        optimizer.step()
        # 统计
        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()
    
    # 计算准确率
    train_accuracy = 100 * correct / total
    
    # 测试模型
    model.eval()
    test_correct = 0
    test_total = 0
    test_loss = 0.0
    
    with torch.no_grad():
        for inputs, targets in test_loader:
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            test_loss += loss.item()
            _, predicted = outputs.max(1)
            test_total += targets.size(0)
            test_correct += predicted.eq(targets).sum().item()
    
    test_accuracy = 100 * test_correct / test_total
    
    # 打印训练信息
    print(f'Epoch [{epoch+1}/{num_epochs}], '
          f'Train Loss: {running_loss/len(train_loader):.4f}, '
          f'Train Acc: {train_accuracy:.2f}%, '
          f'Test Loss: {test_loss/len(test_loader):.4f}, '
          f'Test Acc: {test_accuracy:.2f}%')

# 最终评估
model.eval()
test_correct = 0
test_total = 0

with torch.no_grad():
    for inputs, targets in test_loader:
        outputs = model(inputs)
        _, predicted = outputs.max(1)
        test_total += targets.size(0)
        test_correct += predicted.eq(targets).sum().item()

test_accuracy = test_correct / test_total
print(f"\n测试集准确率: {test_accuracy:.4f}")

# 测试模型预测
print("\n测试模型预测:")
test_sequences = [
    [0, 1, 2],  # 应该预测3
    [3, 4, 5],  # 应该预测6
    [7, 8, 9]   # 应该预测0（因为我们的数据集只到9，这里可能会预测不准确）
]

model.eval()
with torch.no_grad():
    for seq in test_sequences:
        # 准备输入数据
        input_data = torch.tensor(seq, dtype=torch.float32).unsqueeze(0).unsqueeze(-1) / 10.0
        # 预测
        output = model(input_data)
        # 获取预测的类别
        predicted_class = output.argmax().item()
        print(f"输入序列: {seq} -> 预测: {predicted_class}")

# 保存模型
torch.save(model.state_dict(), 'simple_lstm_model.pth')
print("\n模型已保存为 simple_lstm_model.pth")

