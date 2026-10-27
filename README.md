# Finance · 个人金融工作台

A股数据分析 + 盯盘行情的本地客户端，单人使用。前后端分离：

- **backend/** — Python FastAPI（数据源、定时任务、SQLite）
- **frontend/** — Vue 3 + Element Plus + klinecharts + ECharts

## 功能

| 页面 | 内容 |
|---|---|
| 盯盘 | 指数概览、自选列表（盘中 3 秒轮询）、分时图、日/周/月K线（前后复权） |
| 复盘 | 涨停情绪（连板梯队/炸板率/行业聚集）、行业与概念主力资金 5 日榜、沪市 ETF 份额变动，盘后自动快照入库可回看 |
| 估值 | 指数 PE 长序列（2011 起，官网日频）、历史百分位、官方 PE1/PE2/股息率、前 N 大权重股、同花顺一致预期加权 PEG |
| 新闻 | 新闻联播按日归档 + 正文阅读（每日 21:05 自动入库） |
| 详情 | 任意代码的行情、估值、一致预期聚合 + K线 |

## 启动

### 开发模式（改代码热更新）

```bat
scripts\start_dev.bat
```

浏览器打开 **http://127.0.0.1:5173**（后端 8000 由 vite 代理）。

### 单端口模式（日常使用）

```bat
scripts\start.bat
```

浏览器打开 **http://127.0.0.1:8000**（首次会自动构建前端）。

## 环境说明

- Python：系统 3.8 + `backend/.venv`（`--system-site-packages`，复用已装的 pandas/requests/xlrd，
  新装 fastapi/uvicorn/APScheduler）。重建方式：

  ```bat
  cd backend
  python -m venv --system-site-packages .venv
  .venv\Scripts\pip install -r requirements.txt
  ```

- Node：便携版在 `.tools/node`（已配 PATH，仅对启动脚本生效），npm 走 npmmirror。
- 数据库：`backend/data/finance.db`（SQLite，WAL）。删掉即重置。

## 数据源与纪律

- 腾讯财经：实时行情（批量）、日/周/月K（前后复权）、分时
- 东方财富：涨停/炸板/跌停池、行业/概念资金流 —— **一律走 `em_get()` 限流**（1.2s 间隔+抖动+退避重试），防封
- 上交所：ETF 份额日快照（发布有延迟，脚本会自动回退找最近有数据的交易日）
- 中证/上证官网：PE 日频长序列（`indexCsiDsPe`）、官方 PE1/PE2/股息率 xls、成份权重 xls
- 同花顺：个股一致预期 EPS
- 央视：新闻联播条目+文字稿

所有 requests 会话 `trust_env=False`（绕过本机 Clash 系统代理，国内源直连）。

## 定时任务（后端启动即生效）

- 交易日 16:35 抓当日复盘快照（情绪/资金流/ETF份额）
- 周一至周五 21:05 抓新闻联播
- 服务启动时自动补漏（缺最新快照/联播则补抓）

## 目录

```
backend/
  app/
    sources/    # tencent / eastmoney / sse / csindex / ths / cctv（数据源封装）
    api/        # quotes / kline / watchlist / review / valuation / news / profile
    pipelines.py  # 复盘快照、估值入库、联播入库
    jobs.py       # 盘后定时任务 + 启动补漏
    market_clock.py  # 交易日/交易时段（以腾讯日K有无当日bar为准，自动覆盖节假日）
frontend/src/
  views/        # 五个页面
  components/   # QuoteTable / KLineChart / TimelineChart / FlowTable
scripts/        # start_dev.bat / start.bat
```
