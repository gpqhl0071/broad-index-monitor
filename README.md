# 国内宽指基金行情

本地运行的宽基指数 / ETF 实时行情看板。通过浏览器查看上证、深证、科创及海外 QDII 基金的涨跌幅、价格与成交数据，**前后端每 10 秒自动刷新**。

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)

---

## 功能特性

- **多市场分组**：上证 → 深证 → 科创 → 美股（QDII）→ 港股（QDII）
- **实时刷新**：服务端后台拉取 + 内存缓存，前端定时轮询，输出稳定
- **多数据源容错**：8 路公开行情接口轮流主源，失败自动切换备用源
- **零前端构建**：纯 HTML / CSS / JS，改完即生效
- **一键启停**：`start.sh` / `stop.sh` / `restart.sh` 后台守护运行
- **可选天气**：基于 Open-Meteo 的当日与 7 日预报（按 IP 或坐标）

---

## 快速开始

### 环境要求

| 项目 | 说明 |
|------|------|
| Python | 3.9 及以上 |
| 系统 | macOS / Linux（Windows 建议 WSL） |
| 网络 | 可访问东方财富、新浪、腾讯等公开接口 |

### 启动

```bash
cd broad-index-monitor
chmod +x start.sh stop.sh restart.sh

./start.sh          # 后台启动（推荐）
# 浏览器访问 http://127.0.0.1:8765

./stop.sh           # 停止
./restart.sh        # 重启
./start.sh -f       # 前台开发模式（代码热重载）
```

首次运行会自动创建 `.venv` 并安装 `requirements.txt` 中的依赖。

自定义监听：

```bash
HOST=0.0.0.0 PORT=9000 ./start.sh
```

更详细的操作说明、页面字段解释与排错见 **[使用说明.md](./使用说明.md)**。

---

## 项目结构

```
broad-index-monitor/
├── backend/
│   ├── main.py              # FastAPI 入口、路由
│   ├── config.py            # 标的列表与刷新间隔
│   ├── cache.py             # 内存缓存与后台刷新循环
│   ├── fetcher.py           # 数据源调度与 failover
│   ├── weather.py           # 天气接口
│   └── providers/           # 各行情数据源实现
│       ├── eastmoney.py
│       ├── eastmoney_single.py
│       ├── sina.py
│       ├── tencent.py
│       └── tencent_ifzq.py
├── static/
│   ├── index.html           # 行情页面
│   ├── app.js
│   ├── style.css
│   └── weather.js
├── scripts/
│   └── common.sh            # 启停脚本公共配置
├── start.sh                 # 启动
├── stop.sh                  # 停止
├── restart.sh               # 重启
├── requirements.txt
├── 使用说明.md               # 用户使用手册
└── README.md                # 本文件
```

运行时生成（已加入 `.gitignore`）：

- `logs/server.log` — 后台日志
- `.run/server.pid` — 进程 PID

---

## 覆盖标的

在 `backend/config.py` 中配置，默认包含：

| 分组 | 示例 |
|------|------|
| 上证 | 上证指数 000001、沪深300ETF 510300、中证500/1000/2000、红利等 |
| 深证 | 深证成指 399001、创业板ETF 159915、创业板50 159949 |
| 科创 | 科创50ETF 588000 |
| 美股 | 纳指ETF 513100、标普500ETF 513500 |
| 港股 | 恒生科技ETF 513130、恒生医疗ETF 513060 |

增删标的：编辑 `SH_ITEMS` / `SZ_ITEMS` 等列表后执行 `./restart.sh`。

---

## 架构说明

```
浏览器 ──每 10s──► GET /api/quotes ──读缓存──► 内存行情
                        ▲
                        │ 每 10s 后台任务
                        ├── 东方财富 push2（主站 / 延时 / His）
                        ├── 东方财富单票 stock/get
                        ├── 新浪财经 hq.sinajs.cn
                        ├── 腾讯财经 qt.gtimg.cn
                        └── 腾讯 IFZQ fqkline
```

- **FastAPI + Uvicorn**：HTTP 服务与静态资源
- **httpx**：异步请求上游接口
- **QuoteCache**：单例缓存，避免前端直连第三方导致的不稳定

---

## 管理脚本

| 脚本 | 说明 |
|------|------|
| `./start.sh` | 后台启动，日志写入 `logs/server.log` |
| `./start.sh -f` | 前台启动，带 `--reload` |
| `./stop.sh` | 按 PID 或端口停止 |
| `./restart.sh` | 先停后启 |

环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | `127.0.0.1` | 监听地址 |
| `PORT` | `8765` | 监听端口 |

查看日志：`tail -f logs/server.log`

---

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 行情 Web 页面 |
| GET | `/api/quotes` | 当前缓存行情 JSON |
| GET | `/api/health` | 健康检查 |
| GET | `/api/weather?lat=&lon=` | 天气（坐标可选，缺省按客户端 IP 粗定位） |

`GET /api/quotes` 响应示例字段：`items`（行情列表）、`updated_at`、`provider`、`error` 等。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3、FastAPI、Uvicorn、httpx、asyncio |
| 前端 | 原生 HTML / CSS / JavaScript |
| 数据 | 东方财富、新浪、腾讯公开行情接口；Open-Meteo 天气 |

依赖见 [requirements.txt](./requirements.txt)。

---

## 手动安装（可选）

不使用脚本时：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

---

## 常见问题

**页面提示「上游异常」**  
公开接口偶有断连或限流，服务会自动切换数据源。可执行 `./restart.sh` 或稍后重试。

**端口被占用**  
执行 `./stop.sh` 后再 `./start.sh`。

**非交易时段数据为空**  
收盘后部分字段可能为昨收或空值，属正常现象。

---

## 免责声明

本项目数据来自第三方公开接口，**仅供个人学习参考**，非证券交易所或基金公司授权行情。不构成任何投资建议，请勿作为实盘交易的唯一依据。

---

## 相关文档

- [使用说明.md](./使用说明.md) — 安装、启停、页面说明、排错指南
