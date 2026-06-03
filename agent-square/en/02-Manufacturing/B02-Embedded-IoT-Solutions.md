---
name: 嵌入式IoT方案
name_en: Embedded IoT Solutions
type: Composite Application
industry: Manufacturing
composed_of: [数据采集工程师, 云资源管理员, API集成工程师]
source_refs: [Embedded Firmware Engineer(engineering), Mobile App Builder, Backend Architect]
apis: [ThingSpeak, Adafruit IO, HiveMQ]
emoji: 🔌
---

# 🔌 嵌入式IoT方案 Embedded IoT Solutions

## Use Case
消费级/工业级IoT产品方案商: MCU选型→固件→通讯→云平台→移动端。

## Agent Composition
```
[Embedded Firmware Engineer] ← engineering
[Mobile App Builder] ← engineering
[Backend Architect] ← engineering
[数据采集工程师] ← Data Engineer
```

## Bound APIs
| API | Purpose |
|-----|------|
| ThingSpeak | 公有云平台 |
| Adafruit IO | 开发平台 |
| HiveMQ | MQTT Broker |

## 核心工作流
1. **硬件选型**：MCU/sensor/RF
2. **固件开发**：RTOS/裸机
3. **通讯协议**：BLE/WiFi/LoRa/4G
4. **云接入**：MQTT/HTTP
5. **App客户端**：iOS/Android/小程序

## Sample Output
```
【某智能家居方案 出货】
品类: 智能门锁 | 年出货 38万台
硬件BOM:
  - 主控: STM32L4 MCU
  - 通讯: WiFi + BLE5
  - 电源: 4xAA电池 (寿命12月)
  - 指纹模块: 半导体
  - 成本 ¥85
软件:
  - 固件 FreeRTOS
  - BLE配网 + WiFi回传
  - OTA升级
  - 本地+云双模
云:
  - 自建MQTT集群 (2万/秒并发)
  - 日活设备 180万
  - 平均延迟 120ms
App:
  - iOS/Android + 微信小程序
  - 月活 92万
  - 评分 App Store 4.7
售后: 返修率 1.2% (一年)
```
