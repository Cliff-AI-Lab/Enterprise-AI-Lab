<p align="center">
  <img src="https://img.shields.io/badge/Agent_Square-Industry_Collection-0A84FF?style=for-the-badge&labelColor=0D1117" alt="Agent Square — Industry" />
  <img src="https://img.shields.io/badge/Agents-334-00D4AA?style=for-the-badge&labelColor=0D1117" alt="334 Agents" />
  <img src="https://img.shields.io/badge/Sectors-10-7B61FF?style=for-the-badge&labelColor=0D1117" alt="10 Sectors" />
  <img src="https://img.shields.io/badge/Bilingual-ZH_·_EN-58A6FF?style=for-the-badge&labelColor=0D1117" alt="Bilingual" />
</p>

<h1 align="center">Agent Square · Industry Collection</h1>

<p align="center">
  <b>334 production-ready industry-specific AI agents across 10 verticals</b><br/>
  <sub>Finance · Manufacturing · Energy · Healthcare · Retail · Government · Education · Logistics · Technology · Agriculture</sub>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="#sector-overview">Sector Overview</a> ·
  <a href="#naming-system">Naming System</a> ·
  <a href="#file-format">File Format</a> ·
  <a href="#中文版">中文版</a>
</p>

---

## Overview

This directory is the **industry slice** of the *Agent Square* series — 334 vertical agents designed around enterprise scenarios across 10 major sectors. For general-purpose / digital-employee agents (secretary, translation, HR, ESG, etc.), see the companion repo [Ruidong-AI/agent-square](https://github.com/Cliff-AI-Lab/Ruidong-AI/tree/main/agent-square).

Together the two repos make up the full *Agent Square* — **365 agents**, one for every day of the year.

## Sector Overview

| # | Sector | 板块 | Count | Highlights |
|---|--------|------|------:|-----------|
| 01 | Finance | 金融 | 47 | Stocks, bonds, crypto, insurance, banking, funds, credit, ABS, NFT, family office |
| 02 | Manufacturing | 制造 | 40 | Industrial IoT, digital factory, auto, semiconductor, steel, chemicals, liquor, shipbuilding |
| 03 | Energy | 能源 | 32 | PV, wind, nuclear, storage, hydrogen, carbon assets, grid, hydro, LNG |
| 04 | Healthcare | 医药 | 33 | Drug R&D, genomics, hospitals, pharmacy, devices, postpartum, dental, rehab |
| 05 | Retail | 零售 | 34 | E-commerce, livestream, luxury, maternal, alcohol, outdoor, beauty, bridal, trendy toys |
| 06 | Government | 政务 | 28 | 12345 hotline, city management, judicial, census, emergency, civil registry, fire |
| 07 | Education | 教育 | 25 | K12, higher ed, study abroad, kid coding, special-ed, psychology, Go, family |
| 08 | Logistics | 物流 | 25 | City delivery, cross-border, cold chain, air cargo, ports, hazmat, special, trunk |
| 09 | Technology | 科技 | 34 | AIOps, SOC, XR, AIGC, SaaS, low-code, MCP, editing, Serverless |
| 11 | Agriculture | 农牧 | 36 | Smart farm, digital ranch, tea, aquaculture, forestry, honey, TCM herbs, mushrooms |
| | **Total** | | **334** | |

> Note: sector `10-General` (31 general-purpose agents) is published separately in [Ruidong-AI/agent-square](https://github.com/Cliff-AI-Lab/Ruidong-AI/tree/main/agent-square) per our classification: general/digital-employee → Ruidong-AI; industry-specific → Enterprise-AI-Lab.

## Quick Start

### Option 1 — Claude Code Subagent

```bash
cp "en/01-Finance/01-Stock-Analyst.md" ~/.claude/agents/stock-analyst.md
```

### Option 2 — System Prompt

Copy any `.md` file's content and paste it as the system prompt in Claude / ChatGPT / Gemini / domestic LLMs.

### Option 3 — Product / Architecture Reference

Each file is a business blueprint with APIs, workflow, and deliverables — directly usable as a reference for RPA, low-code, or custom business-system design.

### Option 4 — Multi-Agent Orchestration

The `A/B/C/D`-series composites describe multi-agent workflows — ideal as inputs for LangGraph or similar agent-orchestration frameworks.

### Bundle Download

- Chinese: [`agent-square-industries-zh.zip`](agent-square-industries-zh.zip)
- English: [`agent-square-industries-en.zip`](agent-square-industries-en.zip)

## Sector Highlights

### 🏦 Finance (47)
Stock Analyst · Crypto Advisor · Robo-Advisor · Risk & Compliance · AML · Web3 Wallet · Quant Trading · Family Office · IPO Pricing · ESG Investing · Bank Digital Human · REITs · ABS · Private Banking · Crowdfunding · Supply-Chain Finance · Cross-Border Payments

### 🏭 Manufacturing (40)
Production Efficiency Hub · Smart Factory Brain · Digital Twin · Industrial LLM · Quality Traceability · Supply-Chain Resilience · Predictive Maintenance · Auto OEM · Semiconductor Wafer · Textile Digitization · Liquor Brewing · 3D Print Cloud · Shipbuilding · Aerospace Parts · Electronics EMS

### ⚡ Energy (32)
Integrated Energy Service · Virtual Power Plant · PV-Storage · Storage Arbitrage · Charging Network · Hydrogen Full-Chain · Carbon Asset Steward · Nuclear O&M · Offshore Wind · Smart Hydro · LNG Trading · EMC Savings · Geothermal · Oil & Gas Pipeline

### 💊 Healthcare (33)
Drug R&D Assistant · AI Pipeline · Hospital Ops · DTC Clinic · Real-World Evidence · Precision Medicine · TCM AI · Gene Sequencing · Medical Imaging AI · Internet Hospital · Device R&D · Vaccine Traceability · Pharmacy Chain · Orthopedic Rehab · Vision

### 🛒 Retail (34)
Omni-Channel Commerce · Livestream Commerce · New Retail Store · Smart Supply Chain · Trendy-Toy IP · Fresh Produce · Beauty Incubation · F&B Chain · Luxury Resale · Used Book · Alcohol Vertical · Flower Delivery · Outdoor · Guochao · Bridal

### 🏛️ Government (28)
12345 Hotline · City Brain · Smart Transit · Police Assist · Public Health Emergency · Investment Promotion · Judicial Digitization · Smart Party-Building · Smart Urban Mgmt · Tax Audit · Emergency Mgmt · Fire Supervision · Civil Registry / Marriage / Veterans

### 🎓 Education (25)
1-on-1 AI Tutor · Corporate University · Lesson Prep · Career Planning · Vocational Training · Academic Plagiarism · Multilingual Practice · Online Ed · K12 Grading · MOOC · Special Ed · Kid Coding · English Enlightenment · Civil Service Prep · Counseling

### 🚚 Logistics (25)
City Instant · Cold-Chain Full-Link · Cross-Border Brain · Smart Port · Shipping Scheduling · Last Mile · High-Value Security · Multi-Modal · Intra-City Freight · Air Cargo · Express Franchise · Hazmat · Special Transport

### 💻 Technology (34)
AIOps · SOC · Data Governance · LLM App Platform · MCP Server · AI Agent Dev · XR Spatial · Game Studio · Growth Analytics · Low-Code · SaaS · AIGC · Digital Twin City · Serverless

### 🌾 Agriculture (36)
Smart Farm · Digital Ranch · Produce Traceability · Agri-Futures Hedging · Autonomous Farm Machinery · Swine Full-Chain · Deep-Sea Fishery · Tea Full-Chain · Rural Revitalization · Pet Ecosystem · Agri-InsurTech · Smart Forestry · Honey · TCM Herbs · Mushroom

## Naming System

Inside each industry folder, agents use prefix semantics:

- **01–, 02–, …** — Foundation agents (single capability + API binding)
- **A01, A02, …** — Applied composites (multi-agent orchestration + multi-API)
- **B01, B02, …** — Advanced scenarios
- **C01, C02, …** — Niche verticals
- **D01, D02, …** — Long-tail specialists

## File Format

Each `.md` follows a YAML frontmatter + body layout:

```yaml
---
name: 中文名
name_en: English Name
type: 组合应用        # optional
industry: 所属行业
apis: [API list]
emoji: icon
---
```

Body sections:

1. **Application Scenario** — what problem it solves
2. **Core Capabilities / Bound APIs** — what it can do + what it plugs into
3. **Workflow** — step-by-step operation (detailed variants included)
4. **Typical Output** — deliverable samples

## Main API Categories

**Finance**: Alpha Vantage, Finnhub, CoinGecko, ExchangeRate-API, Plaid, Etherscan
**Health**: OpenFDA, ClinicalTrials.gov, PubMed, Disease.sh, NPPES, RxNorm
**Environment**: OpenWeatherMap, OpenAQ, NASA EONET, Carbon Interface, Climatiq
**Government**: Data.gov, SEC EDGAR, USASpending, Federal Register, Congress.gov
**Development**: GitHub, Stripe, HuggingFace, Replicate, VirusTotal, Shodan
**Logistics**: AfterShip, EasyPost, OpenRouteService, ShipEngine, 17track
**Agriculture**: OpenWeatherMap Agro, NASA POWER, OpenFoodFacts, Open Prices

Most APIs offer free tiers — register on each vendor's site to obtain API keys.

## Directory Structure

```
agent-square/
├── zh/
│   ├── 01-金融/   (47)    06-政务/   (28)
│   ├── 02-制造/   (40)    07-教育/   (25)
│   ├── 03-能源/   (32)    08-物流/   (25)
│   ├── 04-医药/   (33)    09-科技/   (34)
│   ├── 05-零售/   (34)    11-农牧/   (36)
├── en/
│   ├── 01-Finance/        06-Government/
│   ├── 02-Manufacturing/  07-Education/
│   ├── 03-Energy/         08-Logistics/
│   ├── 04-Healthcare/     09-Technology/
│   ├── 05-Retail/         11-Agriculture/
├── agent-square-industries-zh.zip
├── agent-square-industries-en.zip
└── README.md
```

---

## 中文版

### 概述

本目录是 *Agent广场* 系列中的**行业部分** —— 覆盖 10 大行业、共 **334 个**垂直场景智能体。通用类（秘书、翻译、HR、ESG 等 31 个数字员工类）发布于姐妹仓库 [Ruidong-AI/agent-square](https://github.com/Cliff-AI-Lab/Ruidong-AI/tree/main/agent-square)。

合起来即完整的 *Agent广场* —— **365 个智能体，一年每天一个**。

### 板块分布

| 序号 | 板块 | 数量 | 说明 |
|------|------|-----:|------|
| 01 | 金融 | 47 | 股票/债券/加密/保险/银行/基金/征信/ABS/NFT/家办 |
| 02 | 制造 | 40 | 工业互联网/数字工厂/汽车/半导体/钢铁/化工/白酒/船舶 |
| 03 | 能源 | 32 | 光伏/风电/核电/储能/氢能/碳资产/电网/水电/LNG |
| 04 | 医药 | 33 | 新药研发/基因/医院/药房/医械/月子/口腔/康复 |
| 05 | 零售 | 34 | 电商/直播/奢侈品/母婴/酒类/户外/美业/婚嫁/潮玩 |
| 06 | 政务 | 28 | 12345/城管/党建/司法/普查/应急/户籍/婚姻/消防 |
| 07 | 教育 | 25 | K12/大学/留学/少儿编程/特殊教育/心理/围棋/家庭 |
| 08 | 物流 | 25 | 城配/跨境/冷链/航空货运/港口/危化品/特种/干线 |
| 09 | 科技 | 34 | AIOps/SOC/XR/AIGC/SaaS/低代码/MCP/剪辑/Serverless |
| 11 | 农牧 | 36 | 智慧农场/数字牧场/茶叶/水产/林业/蜂蜜/中药材/食用菌 |
| | **合计** | **334** | |

### 四种使用方式

1. **Claude Code 子代理**：`cp "zh/01-金融/01-股票分析师.md" ~/.claude/agents/stock-analyst.md`
2. **系统提示词**：复制 md 内容贴到任意大模型的系统提示词位置
3. **产品/架构参考**：每个文件都是带 API、工作流和交付物的业务蓝图，可直接用于 RPA、低代码或业务系统设计
4. **多 Agent 编排**：`A/B/C/D` 系列描述多 Agent 协作场景，适合作为 LangGraph 等编排框架的输入

### 整包下载

- 中文版：[`agent-square-industries-zh.zip`](agent-square-industries-zh.zip)
- English: [`agent-square-industries-en.zip`](agent-square-industries-en.zip)

### 一年一天一个的玩法建议

- **按月排**：1 月金融月、2 月制造月、3 月能源月……
- **按需查**：遇到具体业务场景直接搜
- **按天学**：每天花 15 分钟看一个，积累行业思维模型

### 设计理念

1. **一个智能体 = 角色 + 能力 + 数据**
2. **基础 → 组合** 的进阶路径（数字前缀 → A/B/C/D 系列）
3. **行业场景优先** —— 334 个真实业务锚点
4. **交付物可见** —— 每个文件均含典型输出样例

---

<p align="center">
  <a href="https://github.com/Cliff-AI-Lab/Ruidong-AI"><img src="https://img.shields.io/badge/RuidongAI-More_Projects-0A84FF?style=for-the-badge&logo=github&labelColor=0D1117" alt="RuidongAI" /></a>
  &nbsp;
  <a href="https://x.com/RaytoneAI"><img src="https://img.shields.io/badge/@RaytoneAI-Follow-00D4AA?style=for-the-badge&logo=x&logoColor=white&labelColor=0D1117" alt="X (Twitter)" /></a>
</p>
