---
name: XR空间应用
name_en: XR Spatial Application
type: Composite Application
industry: Technology
composed_of: [AI模型评测师, 数据采集工程师, 数据可视化师]
source_refs: [visionOS Spatial Engineer, XR Immersive Developer, XR Interface Architect, XR Cockpit Interaction Specialist, macOS Spatial/Metal Engineer, Terminal Integration Specialist(spatial-computing)]
apis: [Mapbox, HuggingFace, ThingSpeak]
emoji: 🥽
---

# 🥽 XR空间应用 XR Spatial Application

## Use Case
Apple Vision Pro/Meta Quest/PICO 等XR设备的企业级应用开发(培训/协同/诊断/工业维护)。

## Agent Composition (榨取 spatial-computing 全部6个Agent)
```
[visionOS Spatial Engineer] ← spatial-computing
[XR Immersive Developer] ← spatial-computing
[XR Interface Architect] ← spatial-computing
[XR Cockpit Interaction Specialist] ← spatial-computing
[macOS Spatial/Metal Engineer] ← spatial-computing
[Terminal Integration Specialist] ← spatial-computing
```

## Bound APIs
| API | Purpose |
|-----|------|
| Mapbox 3D | 空间地图 |
| HuggingFace | 视觉/手势识别 |
| ThingSpeak | IoT接入XR |

## 核心工作流
1. **场景建模**：3D环境
2. **交互设计**：手势/语视联动
3. **数据可视化**：空间图表
4. **协同能力**：多人同场
5. **真机适配**：多设备

## Sample Output
```
【某石化企业 XR远程诊断应用】
应用场景: 现场工程师戴Vision Pro + 远程专家
核心功能:
  - 3D设备数字孪生 叠加在实物
  - 远程专家第一视角指导
  - IoT传感数据 空间标注
  - 手册+历史数据 悬浮显示
  - 多人协同标注
用户反馈:
  - 专家差旅减少 70%
  - 诊断时间从平均4小时→1.2小时
  - 一次解决率 92% (对比 78%)
技术:
  - Vision Pro主力 + Quest3备选
  - visionOS 2.0 SDK
  - WebXR协同层 支持异构
  - 延迟<80ms
部署: 42座工厂, 120+专家, 400+现场工程师
```
