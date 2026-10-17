# Lore

**面向 SRE 知识的安全 RAG。** 一个检索增强生成系统,可摄取运维文档、在存储前剥离敏感数据,并
以引用来源的方式回答问题。

[English](README.md) · [Português](README.pt-BR.md) · [简体中文](README.zh-CN.md)

作者:Brenda Tavares · 状态:本地 MVP,未部署 · 质量保障:手动 (§9) · 更新日期:2026-10-17

> 作品集项目。所有密钥都位于被 git 忽略的 `.env` 文件中;本仓库中没有任何密钥被提交。

---

## 1. 问题

运维知识——runbook、事件处理流程、故障排查指南——分散在各种文件和人脑中。当值班工程师在事故期
间需要答案时,搜索时间以停机分钟数来计量。

通用工具在这一场景上失败的原因有三:

- **关键词搜索在模糊回忆上会失败。** 工程师记得的是症状,而不是具体的命令或章节标题。
- **纯 LLM 的回答不可审计。** 凭记忆回答的模型会编造机构自有 runbook 中并不存在的命令,而且
  没有任何东西能暴露这一点。
- **运维文档包含机密。** 真实 runbook 中会出现凭证、令牌和主机名。将它们上传到外部索引,或
  粘贴到聊天界面,都会造成泄露。

Lore 同时解决这三点:基于机构自有文档的语义检索、基于检索上下文且附带引用的回答,以及在**任何
内容被存储之前**对敏感数据进行脱敏。

---

## 2. 设计理据

四个约束塑造了整体架构:

- **可审计性优先于流畅性。** 在运维场景中,没有来源的回答是一种责任风险。每个回答都会返回
  其依据的原文 chunk,并在 UI 中渲染为引用。当检索不到相关内容时,系统会明确说明,而不是临
  时编造。
- **脱敏应在持久化之前,而非之后。** 脱敏运行在摄取流水线中,在 chunking 和嵌入之前完成。一
  个从未进入向量存储的机密,任何后续组件都无法检索、回显或泄露。
- **隔离应当来自结构,而非约定。** 多租户被强制作为每个向量查询的必要过滤条件,而非开发人
  员可能遗忘的可选参数。当前租户是一个固定的开发标识符;身份认证已列入路线图 (§10、§14)。
- **零基础设施开发,生产路径成文。** Qdrant 以嵌入式(本地路径)模式运行,使 MVP 不需要任何
  额外服务。向 Qdrant 服务器和托管 Postgres 的迁移路径已在文档中明确说明 (§13),而不是被
  默认为存在。

---

## 3. 解决方案

一个双流水线系统,配有三种语言的界面:

**摄取流水线。** 上传 → MIME 白名单校验 → 机密/PII 脱敏 → 带重叠的滑动窗口 chunking → 嵌入
(OpenRouter,带磁盘缓存、批处理和指数退避) → PostgreSQL(文档与 chunk 元数据) + Qdrant(带租
户负载的向量)。

**检索流水线。** 提问 → 相同嵌入模型 → 租户过滤的向量搜索 → 前 5 个 chunk → 提示词组装(依据
指令 + 上下文 + 问题) → Groq LLM → Markdown 格式的回答,并附引用来源。

**界面。** 一个 PT-BR / EN / ZH-CN 的 React 单页应用,暴露上传与聊天功能,渲染 Markdown 和引
用,从不接触 API 密钥。

---

## 4. 技术栈

| 层级 | 选型 | 原因 |
| --- | --- | --- |
| 前端 | React 18 + TypeScript、Vite、Tailwind CSS 3(加 typography 插件)、axios、react-markdown、lucide-react | 单页工具界面;TypeScript 提供契约安全;Tailwind 无需组件库即可得到一致的设计系统 |
| 后端 | FastAPI (Python 3.11)、Pydantic Settings v2 | 异步 API 配合类型化校验;设置从显式的 env 文件路径解析 |
| 关系库 | PostgreSQL、SQLAlchemy 2 (psycopg2) | 具有关系完整性的文档与 chunk 元数据 |
| 向量库 | Qdrant,本地路径嵌入模式 | 零基础设施开发;负载过滤使得强制租户隔离成为可能;服务器模式已在文档中说明用于生产 |
| 嵌入 | OpenRouter (`liquid/lfm-2.5-embedding-350m:free`),磁盘缓存、批处理、退避 | 成本受限的免费额度;缓存消除重复调用;批处理降低请求数量 |
| LLM | Groq (`openai/gpt-oss-120b`) | 聊天路径上的低延迟推理 |
| i18n | 内联字典(26 个键 × 3 个语种)、React Context、localStorage | 无库依赖;与作者作品集中其它项目一致的零依赖方案 |

---

## 5. 架构

```
摄取
浏览器 ──multipart──▶ FastAPI ──▶ MIME 白名单 ──▶ 脱敏 ──▶ chunking
                              │
                              ▼
                  嵌入 (OpenRouter:缓存 / 批处理 / 退避)
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
          PostgreSQL                 Qdrant (嵌入式)
       文档, chunk                 向量 + 租户负载

检索
浏览器 ──问题──▶ FastAPI ──▶ 问题嵌入 ──▶ Qdrant 检索 (租户过滤,top-5)
                              │
                              ▼
                 提示词 = 依据指令 + chunks + 问题
                              │
                              ▼
                        Groq LLM ──▶ 回答 (Markdown) + 来源
```

| 接口 | 用途 |
| --- | --- |
| `POST /api/v1/documents/upload` | 带校验和脱敏的 multipart 摄取 |
| `POST /api/v1/ai/chat` | 附带引用来源的依据式回答 |
| `GET /health` | 存活探针 |
| `GET /docs` | OpenAPI / Swagger UI |

---

## 6. 安全模型

| 控制点 | 实现方式 |
| --- | --- |
| 租户隔离 | 每个向量查询都带有强制的 `tenant_id` 过滤条件;跨租户检索在服务层无法表达 |
| 机密脱敏 | 凭证、令牌、PII 模式在摄取过程中、在 chunking 和嵌入之前被剥离 |
| 上传校验 | 服务端 MIME 白名单 (`.md`、`.txt`、`.pdf`);类型在服务端校验,从不信任客户端 |
| CORS | 显式的来源白名单(仅限开发来源);不使用通配符 |
| 密钥处理 | 所有密钥位于 git 忽略的 `.env`;env 文件通过绝对路径解析,防止应用在环境为空时静默启动 |
| 依据式回答 | 系统指令禁止在检索上下文之外回答;来源伴随每个回答返回 |
| 外部 API 边界 | 嵌入缓存、批处理、指数退避;`MAX_CHUNKS_PER_QUERY` 限制上下文规模和成本 |
| 可审计性 | 引用暴露每个回答的确切依据 chunk |

---

## 7. 检索:它是什么(以及不是什么)

- **这是真正的 RAG。** 嵌入、向量搜索、上下文注入、引用——不是伪装成检索的静态提示词块。
- **检索是语义的,不是词法的。** 查询使用与摄取时相同的嵌入模型;排序是基于向量的相似度,按
  租户过滤。
- **重叠会产生近重复项。** 滑动窗口 chunking 意味着同一文档的多个 chunk 都可能进入 top-5。
  UI 按 `(filename, snippet)` 对引用去重;后端去重已列入路线图。
- **它不是微调,也不是知识图谱。** 模型对文档的记忆仅限于每次请求所注入的上下文。
- **回答语言跟随文档语言。** i18n 只覆盖界面 (§8)。

---

## 8. 国际化

三种语种——PT-BR、EN、ZH-CN——每种 26 个键,无 i18n 库。

- 首次访问通过 `navigator.language` 自动检测。
- 界面内的切换器覆盖选择,并将其持久化到 `localStorage`。
- 回退链:当前语种 → 英语 → 原始键(可见的键即为可检测的缺陷)。
- 切换时更新 `document.documentElement.lang`,以兼顾可访问性与 SEO。

范围说明:i18n 翻译的是**界面**。LLM 的回答取决于摄取文档的语言。

---

## 9. 质量保证

### 9.1 当前状态:手动

质量保证**手动**进行。目前还没有自动化套件;其路线图见 §9.3。以下清单在每次变更时都会被执行:

| 检查项 | 验证方式 |
| --- | --- |
| 上传正向路径 | `.md` 上传返回文档 id;摄取日志完成 |
| 非法 MIME 被拒绝 | 不在白名单的类型返回校验错误 |
| 脱敏 | 含有假令牌的文档被摄取;令牌不出现在存储的 chunk 和引用中 |
| 依据式回答 | 聊天返回与 runbook 一致的回答,并附来源 |
| 引用去重 | 单文档语料库产生一个引用块,而非五个 |
| i18n 一致性 | 切换器在不重载的情况下,在 PT、EN、ZH 中渲染所有 UI 字符串 |
| CORS | 来自非白名单来源的请求被浏览器阻止 |
| 限流恢复 | 摄取过程中的 429 通过退避恢复,不丢数据 |
| 设置加载 | 应用以仓库根的 `.env` 启动,与进程 CWD 无关 |
| 优雅关闭 | Ctrl+C 停止后不留下端口或 Qdrant 锁 |

### 9.2 事故日志(开发期缺陷与过程失败)

默默修复的缺陷无法教会任何人。以下事故记录了根因与防护措施。1–7 为产品或配置缺陷;第 8 项为
工具/过程事故,单独分类,因为它从未进入产品。

| # | 症状 | 根因 | 处理与防护 |
| --- | --- | --- | --- |
| 1 | 设置加载为空 (`ValidationError`,`input_value={}`) | pydantic-settings 中的 `env_file = ".env"` 相对于进程 CWD 解析;文件被移到仓库根,而服务器从 `src/` 启动 | env 文件改为基于模块位置的绝对路径;手动 QA 中加入"从根启动"检查 |
| 2 | 服务器"启动"但不服务;启动挂起 | 一个旧 Python 进程在终端未用 Ctrl+C 关闭后,仍占用 8000 端口和 Qdrant 嵌入式文件锁 | 杀死进程;操作规则:始终用 Ctrl+C 停止;Qdrant 嵌入式模式记为单进程 |
| 3 | 摄取期间嵌入调用报 HTTP 429 | 免费额度提供商的限流 | 指数退避重试、磁盘嵌入缓存、批处理嵌入;上下文受 `MAX_CHUNKS_PER_QUERY` 限制 |
| 4 | 编辑器与 Vite 报未知编译选项 (`erasableSyntaxOnly`、`noUncheckedSideEffectImports`、`tsBuildInfoFile` 缺 `incremental`) | Vite 模板使用了比本地 TypeScript 工具链更新的 flag | tsconfig 集合固定为保守、工具链兼容的配置 |
| 5 | `npx tailwindcss init -p` 失败 ("could not determine executable");Markdown 渲染无样式 | 二进制解析失败;`@tailwindcss/typography` 缺失导致 `prose` 类无作用 | 手写配置文件;观察到无样式 Markdown 后添加 typography 插件 |
| 6 | 前端请求被 CORS 阻止 | 白名单早于 Vite 开发来源 (5173) | 白名单加入显式开发来源;刻意不使用通配符 |
| 7 | 同一文档在一次回答中被引用多达五次 | 滑动窗口重叠产生近相同 chunk,全部进入 top-5 | UI 层按 `(filename, snippet)` 去重;后端去重列入路线图 |
| 8 | 过程事故:PowerShell here-string 分隔符污染了源码文件;一个模块被放到错误目录,破坏 import 解析 | here-string 会展开反引号和 `${}`;分隔符落入文件内容;手工放置错误 | 规则:源码文件只在编辑器中创建,永不通过 shell 重定向;写入后校验(检查首尾行)。归类为工具/过程失败,而非产品缺陷 |

### 9.3 自动化 QA 路线图

- `pytest` 套件,覆盖脱敏、chunking、租户过滤、MIME 校验。
- Vitest + Testing Library,覆盖前端组件。
- GitHub Actions CI,在每次推送时运行套件。
- i18n 一致性检查,断言所有语种共享相同的键集合。

---

## 10. 诚实的边界

- **未部署。** 本地 MVP,出于决策;部署策略已记录,但未执行 (§13)。
- **尚无身份认证。** 租户是一个固定的开发标识符。隔离在服务层被强制,但没有登录;JWT 是路线图
  第一项。该实例不得暴露于不可信网络。
- **嵌入式 Qdrant 是单进程的。** 不适用于并发 worker 或水平扩展;服务器模式是生产路径。
- **仅手动 QA。** 尚无自动化套件 (§9.3)。
- **免费额度模型**是基于成本边界选择的,而非基准领先。
- **引用去重发生在 UI 端。** 后端仍可能返回冗余 chunk。
- **PDF 摄取被接受,但尚未纳入手动 QA。** Markdown 与纯文本是经过验证的路径。

---

## 11. 项目结构

```
lore-rag/
├── src/                      FastAPI 后端
│   ├── app/
│   │   ├── api/v1/           路由:documents、ai/chat
│   │   ├── core/             设置 (pydantic-settings)、安全常量
│   │   ├── db/               SQLAlchemy base 与 session
│   │   ├── models/           关系模型
│   │   ├── services/         摄取、脱敏、chunking、嵌入、
│   │   │                     向量存储、RAG 编排
│   │   └── main.py           App factory、CORS、lifespan
│   └── run.py                开发入口
├── front-end/                React SPA (Vite)
│   ├── src/
│   │   ├── components/       Chat、FileUpload、LanguageSwitcher
│   │   ├── i18n/             I18nContext + locales (pt-BR、en、zh-CN)
│   │   ├── services/api.ts   Axios 客户端
│   │   └── types/            共享 TypeScript 类型
│   └── ...
├── .env                      git 忽略;永不提交
└── README.md / README.pt-BR.md / README.zh-CN.md
```

---

## 截图

### 主界面

<p align="center">
  <img src="docs/screenshots/interface.png" alt="Lore 主界面:上传与对话" width="800" />
</p>

<p align="center">
  <em>文档上传与 RAG 对话,并附引用来源。</em>
</p>

---

### 文档上传

<p align="center">
  <img src="docs/screenshots/upload-success.png" alt="文档上传成功提示" width="800" />
</p>

<p align="center">
  <em>完整流水线:MIME 校验、脱敏、分块与向量化。</em>
</p>

---

### 带引用的 RAG 对话

<p align="center">
  <img src="docs/screenshots/chat-response.png" alt="带引用来源的对话回答" width="800" />
</p>

<p align="center">
  <em>基于检索上下文的依据式回答,所引用的 chunk 已经过 UI 去重。</em>
</p>

---

### 国际化

<p align="center">
  <img src="docs/screenshots/language-switcher.png" alt="语言切换器 PT/EN/ZH" width="800" />
</p>

<p align="center">
  <em>语言切换器,支持自动检测并将选择持久化至 localStorage。</em>
</p>

---

## 12. 启动指南

### 前置要求

- Python 3.11+、Node 18+、本地运行的 PostgreSQL
- API 密钥:OpenRouter (嵌入)、Groq (聊天)

### 后端

```bash
cd src
python -m venv ../venv
../venv/Scripts/Activate.ps1        # Windows;Unix 使用 bin/activate
pip install -r requirements.txt
python run.py                       # http://127.0.0.1:8000  (Swagger 位于 /docs)
```

### 前端

```bash
cd front-end
npm install
npm run dev                         # http://localhost:5173
```

两个进程必须同时运行,分别位于各自的终端。使用 Ctrl+C 停止;在进程运行时关闭终端可能导致端口
或 Qdrant 锁被占用 (§9.2,事故 2)。

### 环境变量 (`.env` 位于仓库根,永不提交)

| 变量 | 用途 |
| --- | --- |
| `DATABASE_URL` | PostgreSQL 连接字符串 |
| `OPENROUTER_API_KEY` | 嵌入提供商 |
| `GROQ_API_KEY` | 聊天 LLM 提供商 |
| `EMBEDDING_MODEL` / `DEFAULT_LLM_MODEL` | 模型标识符 |
| `QDRANT_PATH` | 嵌入式向量存储目录 |
| `MAX_CHUNKS_PER_QUERY` | 检索上限(上下文规模与成本) |
| `RATE_LIMIT_PER_MINUTE` | 应用级限流设置 |
| `SECRET_KEY` | 应用密钥 |
| `APP_NAME` / `DEBUG` | 元数据与调试开关 |

---

## 13. 部署状态与策略

未部署,出于决策。为未来的生产运行评估了三种策略:

| 策略 | 形态 | 取舍 |
| --- | --- | --- |
| VPS + Docker Compose | 应用、PostgreSQL、Qdrant 服务器三个容器;数据放在 volume | 成本最低、完全控制、可展示容器化;备份由你负责 |
| 全托管 | PaaS 应用 + 托管 Postgres + Qdrant Cloud | 零运维;成本更高,可展示的工程含量更少 |
| 混合 | PaaS 应用 + 托管 Postgres + 容器化 Qdrant | 折中;无状态 PaaS 上的 volume 是向量数据的陷阱 |

任何生产运行所需的变更:Qdrant 客户端改为双模式(设置时使用 `QDRANT_URL` + `QDRANT_API_KEY`,否则
走嵌入式路径);`DATABASE_URL` 指向托管实例;JWT 身份认证替换开发租户;带 HTTPS 的反向代理;
按用户限流;备份与监控策略。

---

## 14. 路线图

- JWT 身份认证(替换开发租户标识符)
- 自动化测试套件与 CI (§9.3)
- 后端级引用去重
- 本地开发 Docker Compose(PostgreSQL + Qdrant 服务器)
- 手动 QA 覆盖 PDF 摄取
- 执行其中一种部署策略 (§13)

---

## 15. 许可证与作者

MIT。见 `LICENSE`。

**Brenda Tavares** — 后端工程师
巴伊亚联邦大学 (UFBA) 人文学士
Pitágoras Unopar Anhanguera 大学 后端开发
GitHub:https://github.com/Brenda-Tavares
LinkedIn:https://www.linkedin.com/in/brenda-campos-tavares/
联系方式:tavaresbrenda@proton.me

嵌入由 OpenRouter 提供;推理由 Groq 提供;向量库由 Qdrant (开源) 提供。所有提供商密钥均由调用方
提供,永不提交。