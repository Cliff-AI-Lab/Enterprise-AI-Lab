---
name: 工业互联网分析师
name_en: Industrial IoT Analyst
type: Composite Application
industry: Manufacturing
composed_of: [数据采集工程师, 云资源管理员, AI模型评测师]
apis: [ThingSpeak, Adafruit IO, HuggingFace]
emoji: 🌐
---

# 🌐 工业互联网分析师 Industrial IoT Analyst

## Use Case
工厂海量IoT数据的清洗、建模、异常检测平台化服务。

## Agent Composition
```
[数据采集工程师] → 多协议接入
[云资源管理员] → 弹性存储/计算
[AI模型评测师] → 异常检测模型评估
```

## Bound APIs
| API | Purpose |
|-----|------|
| ThingSpeak | FreeIoT平台 |
| Adafruit IO | 传感器数据 |
| HuggingFace | 时序模型推理 |

## 核心工作流
1. **协议统一**：OPC-UA/Modbus/MQTT
2. **数据清洗**：去噪/归一化
3. **特征工程**：滑窗/FFT频谱
4. **建模**：LSTM/Prophet/IsolationForest
5. **预警**：分级推送

## Sample Output
```
【工业数据平台周报 Week 16】
数据量: 52亿点/周 (增速+8%)
接入设备: 3,240台 (新增68)
模型效果:
  - 设备异常检测F1: 0.89
  - 能耗预测MAPE: 3.8%
  - 质量预测准确率: 91.2%
本周发现:
  - 分厂B 压缩机能效下降3% → 运维介入
  - 分厂C 注塑机模具温度异常 → 避免批量不良
成本:
  - 云存储: $2,400/月 (热温冷分层)
  - 推理: $600/月
下周计划: 新接入厂区D (126台设备)
```
