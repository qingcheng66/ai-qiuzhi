# ai-qiuzhi — AI 求职助手

输入 JD → 匹配个人知识库 → AI 生成针对性简历 → 多格式导出。同时提供求职进度管理（公司工作台）。

## 快速开始

```bash
./start.sh      # 一键启动（自动装依赖 + 初始化数据库 + 导入知识库）
```

- 前端：http://localhost:5173
- 后端 API：http://localhost:8000/docs

## 主要功能

| 模块 | 说明 |
|------|------|
| **简历生成向导** | 三步：输入 JD（粘贴文本 / 图片 OCR）→ 知识库匹配 + AI 生成 → 选模板预览 / 编辑 / 导出 |
| **个人知识库** | 应用内可编辑：个人信息 / 项目经历 / 技能 / 技术亮点 / 工作经历，支持 Markdown 与 JSON 批量导入 |
| **公司工作台** | 按公司/岗位管理投递，10 阶段状态机（投递→测评→笔试→简历评估→一面→二面→三面→HR面→Offer评估→Offer），面试记录，统计面板 |
| **模板系统** | 3 套内置模板（简约/双栏/技术风）+ 上传 PDF/Word 自动生成可复用模板 |
| **AI 多供应商** | DeepSeek / OpenRouter（OpenAI 兼容）；未配置 key 时自动降级为 Mock，全链路可调试 |

## 技术栈

- 后端：Python 3.11+ / FastAPI / SQLAlchemy 2 / Alembic / WeasyPrint / PyMuPDF / python-docx
- 前端：Vue 3 + TypeScript + Tailwind CSS + Pinia + Vite
- 数据库：SQLite（开发）→ PostgreSQL（生产，改 `DATABASE_URL`）

## 配置

复制 `backend/.env.example` 为 `backend/.env`，按需配置：

| 变量 | 说明 |
|------|------|
| `LLM_PROVIDER` | `deepseek` / `openrouter` / `mock`（默认） |
| `DEEPSEEK_API_KEY` / `OPENROUTER_API_KEY` | 任一配置即启用真实 AI，都未配置则走 Mock |
| `MINERU_OCR_TOKEN` | 可选，MinerU 文档解析（PDF 优先） |
| `BAIDU_OCR_API_KEY` / `TENCENT_OCR_SECRET_ID` | 可选，未配置时 JD 仅支持粘贴文本 |
| `DATABASE_URL` | 生产切换到 PostgreSQL 连接串 |

### OCR 方案

OCR 优先级：**PaddleOCR（本地）> MinerU > 百度OCR > 腾讯OCR > Mock**

- **PaddleOCR**（推荐）：本地运行，无需 API Key。需 Python 3.12 独立环境：
  ```bash
  cd backend && /opt/homebrew/bin/python3.12 -m venv ocr_worker/.venv
  ocr_worker/.venv/bin/pip install paddlepaddle paddleocr
  ```
  安装后自动生效，首次运行会下载约 200MB 模型文件。
- **MinerU**：需 token，适合 PDF 文档解析
- **百度/腾讯 OCR**：需 API Key，代码已实现，填 key 即用

## 数据源导入

首次启动自动执行 `backend/scripts/import_wiki.py`，从用户本地文件导入：

- `/Users/apple/resume/resume.json` — 结构化简历（→ 应用内知识库 + wiki 缓存）
- `/Users/apple/knowledge/career/resume-highlights.md` — 24 条技术亮点
- 2 份针对性简历文档

若本地路径变化，可修改脚本顶部 `RESUME_JSON` / `CAREER_DIR` 后重跑：

```bash
cd backend && .venv/bin/python -m scripts.import_wiki
```

## 项目结构

```
ai-qiuzhi/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── config.py          # 配置（支持 .env）
│   │   ├── models/            # SQLAlchemy 模型（17 表）
│   │   ├── routers/           # API 路由（ocr/jd/wiki/resume/kb/workspace/templates）
│   │   ├── services/          # 业务逻辑（ocr/ai/wiki/knowledge/export/template）
│   │   ├── core/              # llm 多供应商 + 10 阶段状态机
│   │   └── template_static/   # 内置简历模板（minimal/twocolumn/tech）
│   ├── scripts/import_wiki.py # 知识库导入
│   ├── data/                  # SQLite 数据库
│   └── alembic/               # 数据库迁移
├── frontend/
│   └── src/
│       ├── views/             # 7 个页面
│       ├── components/        # Markdown 编辑器/预览组件
│       ├── stores/ router/ api/
└── start.sh                   # 一键启动
```

## 常用命令

```bash
# 后端测试
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

# 前端开发
cd frontend && npm run dev

# 前端类型检查 / 构建
cd frontend && npm run typecheck && npm run build

# 数据库迁移
cd backend && .venv/bin/alembic revision --autogenerate -m "desc"
cd backend && .venv/bin/alembic upgrade head
```