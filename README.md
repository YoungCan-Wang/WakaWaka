# WakaWaka ⚽

WakaWaka 是一个轻量级的足球赔率分析与投注计算工具。它采用 **“本地数学求解器 + AI 视觉 Agent 技能”** 的协作模式，无需购买或配置昂贵的 API Key，直接利用您 IDE（如 Cursor、Codex、Antigravity）内置的 AI 视觉能力，解析投注盘口截图并智能计算最佳的投注策略。

---

## 🌟 核心功能

1. **跨盘口无风险套利 (Surebet) 求解**：
   - 自动检测并组合 1X2、亚洲让球盘 (AH)、大小球 (OU)、双重机会 (DC)、平局退款 (DNB) 等市场。
   - 使用线性规划（LP Solver）智能计算最佳资金分配比例，锁定保障收益（期望收益率 > 1.0）。
2. **基于凯利公式的价值投注 (Value Bet) 推荐**：
   - 如果您能预估某些比分或赛果的真实概率，工具将根据凯利准则自动计算单项投注的期望价值（EV）及推荐本金比例。
3. **AI Vision 协同工作（免 API Key）**：
   - 只要把盘口截图发送给您的 AI 助手，AI 就会利用其视觉模型识别数据并生成 `odds.json`，随后一键运行本地求解器。

---

## 🛠️ 安装与配置

本项目基于 Python 3.9+ 运行。

1. **克隆项目并进入目录**：
   ```bash
   cd WakaWaka
   ```

2. **创建并激活虚拟环境**：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **安装依赖项**：
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 使用指南

### 方式 A：通过 AI 视觉自动解析截图 (推荐)

1. 将足球赔率截图拖入 AI 助手的聊天框（Cursor / Antigravity / Codex）。
2. 发送如下指令给 AI：
   > “请使用 `soccer_betting_skill.md` 里的技能指令解析这张图片，并运行本地求解器。”
3. AI 助手将自动在本地生成 `odds.json`，运行计算命令并把最优投注策略格式化输出给您。

### 方式 B：手动录入赔率

如果您没有截图，或者想手动计算，只需在根目录下创建/编辑 `odds.json`：

```json
{
  "match_info": {
    "home_team": "Manchester City",
    "away_team": "Real Madrid",
    "league": "UCL"
  },
  "selections": [
    {
      "id": "bet365_home",
      "bookmaker": "Bet365",
      "market_type": "1X2",
      "name": "Home",
      "odds": 2.15
    },
    {
      "id": "pinnacle_x2",
      "bookmaker": "Pinnacle",
      "market_type": "DC",
      "name": "X2",
      "odds": 1.95
    }
  ]
}
```

然后在终端运行：
```bash
./.venv/bin/python solver.py odds.json
```

### 方式 C：进行价值投注计算 (EV)

若想利用您的胜率预测寻找期望价值大于 1 的投注项：
1. 创建 `probs.json` 文件指定您的概率预测（比如让球 GD 状态分布，GD 从 -4 到 +4，负数代表客赢，正数代表主赢，总和需为 1.0）：
   ```json
   {
     "gd_probs": {
       "-4": 0.0,
       "-3": 0.05,
       "-2": 0.10,
       "-1": 0.15,
       "0": 0.25,
       "1": 0.25,
       "2": 0.15,
       "3": 0.05,
       "4": 0.0
     }
   }
   ```
2. 运行 `./.venv/bin/python solver.py`，程序在列出套利组合的同时，会特别高亮输出 EV > 1 的高价值单项投注及最优凯利下注比例。

---

## 📂 项目结构

- **[solver.py](file:///Users/youngcan/stock/WakaWaka/solver.py)**: 包含核心计算引擎（LP 规划、凯利公式和终端结果展示）。
- **[soccer_betting_skill.md](file:///Users/youngcan/stock/WakaWaka/soccer_betting_skill.md)**: AI 助手的 Prompt 指引。
- **[requirements.txt](file:///Users/youngcan/stock/WakaWaka/requirements.txt)**: 包含 `scipy` 和 `pydantic` 等依赖。
- **[.gitignore](file:///Users/youngcan/stock/WakaWaka/.gitignore)**: 忽略临时生成的 `odds.json` 以及 `.venv` 环境。
