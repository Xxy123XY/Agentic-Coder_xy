# Multi-Agent Orchestrator

You open a GitHub issue. An autonomous pipeline reads it, finds the relevant code, writes a fix, tests it in an isolated Docker container, and opens a Pull Request — without you touching a keyboard again until the final approval.

This is not a chatbot wrapper. It is a stateful, fault-tolerant engineering pipeline built on the same architectural patterns used by Cognition (Devin), Cursor, and SWE-agent.

```
GitHub Issue  ──►  6 specialized agents  ──►  Pull Request
```

---

## What actually happens

A developer opens issue #42: *"Login fails when email contains uppercase letters"*

```
1. IssueAnalyzer    reads the issue → extracts module: "auth", severity: "high",
                    keywords: ["login", "email", "case", "authenticate"]

2. CodebaseExplorer searches the codebase via RAG → finds auth/login.py lines 34-67,
                    utils/email.py lines 12-28 as most relevant

3. FixDrafter       receives the buggy code + issue context → generates a unified diff
                    fixing email.lower() before comparison

4. TestWriter       sees the diff → writes pytest cases covering:
                    uppercase email login, mixed-case, edge cases

5. Validator        runs pylint + mypy on the generated code → no type errors, no lint issues

6. Docker Sandbox   spins an isolated container, runs pytest → 4 passed, 0 failed

7. Human Review     pipeline pauses → you see the diff in the dashboard → click Approve

8. PRCreator        creates branch fix/issue-42, commits the fix + tests,
                    opens PR: "Fix: Login fails when email contains uppercase letters"
                    Closes #42
```

Total time: ~45 seconds. Zero code written by a human.

---

## Architecture

```
                        ┌──────────────────────────────────────┐
                        │         LangGraph StateGraph          │
                        │                                        │
  GitHub Issue          │  ┌─────────────┐                      │
  (webhook / API)  ───► │  │IssueAnalyzer│                      │
                        │  └──────┬──────┘                      │
                        │         │                              │
                        │  ┌──────▼──────────┐                  │
                        │  │CodebaseExplorer  │ ◄── ChromaDB    │
                        │  │  (RAG search)    │     + embeddings │
                        │  └──────┬───────────┘                  │
                        │         │                              │
                        │  ┌──────▼──────┐   retry (max 3)      │
                        │  │ FixDrafter  │ ◄────────────────┐   │
                        │  └──────┬──────┘                  │   │
                        │         │                          │   │
                        │  ┌──────▼──────┐                  │   │
                        │  │ TestWriter  │                  │   │
                        │  └──────┬──────┘                  │   │
                        │         │                          │   │
                        │  ┌──────▼──────┐  fail ───────────┘   │
                        │  │  Validator  │                       │
                        │  │pylint+mypy  │                       │
                        │  └──────┬──────┘                       │
                        │         │ pass                         │
                        │  ┌──────▼──────┐  fail ───────────────┘
                        │  │   Docker    │
                        │  │  Sandbox   │
                        │  │  (pytest)   │
                        │  └──────┬──────┘
                        │         │ pass
                        │  ┌──────▼──────┐
                        │  │   Human     │ ◄── interrupt()
                        │  │   Review    │     pipeline pauses here
                        │  └──────┬──────┘
                        │         │ approved
                        │  ┌──────▼──────┐
                        │  │  PRCreator  │
                        │  └──────┬──────┘
                        └─────────┼────────────────────────────┘
                                  │
                                  ▼
                            Pull Request
```

**The retry loop is the key detail.** When Validator finds type errors, or Docker tests fail, the graph routes back to FixDrafter with the failure output attached. The next attempt is smarter because it has seen what went wrong. This is not infinite retry — state tracks `retry_count`, hard cap at 3.

**The `interrupt()` before PRCreator is non-negotiable.** LangGraph pauses the graph, serializes the entire state to SQLite, and waits. You review the diff in the dashboard. Approve → PR opens. Reject → pipeline ends. No LLM opens a PR without human sign-off.

---

## Tech stack — and why

Every choice here is free tier or open source.

| Layer | Tool | Why this, not something else |
|---|---|---|
| Orchestration | LangGraph | Stateful graph with conditional edges + checkpointing. Not LangChain chains — those cannot loop, retry, or pause for humans |
| LLM (reasoning) | Groq llama-3.3-70b | Free tier, ~300 tokens/sec, no GPU needed on our side |
| LLM (code) | Groq qwen-2.5-coder-32b | Specialized code model. Outperforms general Llama on diff generation |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | 80MB, CPU-only, no API key, runs offline |
| Vector DB | ChromaDB | Local persistent store, zero config, no separate server |
| Code chunking | tree-sitter | Parses actual AST — splits by function/class boundaries. Line splitters break context |
| Code execution | Docker + docker-py | Isolated containers with network disabled, memory capped, hard timeout |
| API | FastAPI | Async-native, auto-generates OpenAPI docs, Pydantic integration |
| State persistence | SQLite via langgraph-checkpoint-sqlite | Crash recovery. Mid-pipeline server restart → resumes from last node |
| GitHub | PyGithub | Full repo access, PR creation, issue reading |
| Logging | structlog | JSON-structured logs with run_id, agent_name, duration on every line |

**Total cost: $0.** No OpenAI, no paid vector DB, no cloud GPU.

---

## Project structure

```
backend/
├── app/
│   ├── agents/              6 agents — one file each, one responsibility each
│   │   ├── base.py          abstract class: all agents share logging + error handling
│   │   ├── issue_analyzer.py
│   │   ├── codebase_explorer.py
│   │   ├── fix_drafter.py
│   │   ├── test_writer.py
│   │   ├── validator.py
│   │   └── pr_creator.py
│   │
│   ├── graph/               LangGraph wiring
│   │   ├── state.py         TypedDict — the shared contract between all agents
│   │   ├── builder.py       StateGraph construction — all nodes + edges in one place
│   │   ├── edges.py         conditional routing logic (retry/pass/fail decisions)
│   │   └── checkpointer.py  SQLite persistence
│   │
│   ├── rag/                 codebase understanding
│   │   ├── chunker.py       tree-sitter: splits code at function/class boundaries
│   │   ├── embedder.py      sentence-transformers: text → vectors
│   │   ├── vector_store.py  ChromaDB: index + search
│   │   └── retriever.py     high-level interface used by agents
│   │
│   ├── sandbox/             isolated code execution
│   │   ├── executor.py      Docker container lifecycle (spawn, copy files, kill, cleanup)
│   │   ├── runner.py        pytest-specific workflow
│   │   └── parser.py        pytest stdout → structured pass/fail/error counts
│   │
│   ├── github/              GitHub integration
│   │   ├── client.py        PyGithub singleton
│   │   ├── webhook.py       HMAC-SHA256 signature verification
│   │   └── pr.py            branch + commit + PR creation
│   │
│   ├── llm/                 model abstraction
│   │   ├── router.py        picks model by task type (reasoning vs code)
│   │   └── groq_client.py   async Groq wrapper with retry + JSON mode
│   │
│   ├── api/                 HTTP layer
│   │   ├── routes/
│   │   │   ├── issues.py    POST /api/v1/issues/solve
│   │   │   ├── jobs.py      GET /api/v1/jobs, POST /api/v1/jobs/{id}/approve
│   │   │   └── webhooks.py  POST /api/v1/webhooks/github
│   │   └── websocket.py     WS /ws/jobs/{id} — live agent event streaming
│   │
│   ├── db/                  persistence
│   │   ├── models.py        SQLAlchemy Job model
│   │   └── session.py       async session factory
│   │
│   ├── observability/
│   │   ├── logger.py        structlog setup (JSON in prod, pretty in dev)
│   │   └── metrics.py       Prometheus /metrics endpoint
│   │
│   ├── schemas/             Pydantic shapes
│   │   ├── issue.py         IssueAnalysis, IssueContext
│   │   ├── job.py           JobSummary, JobDetail, JobCreateRequest
│   │   └── events.py        AgentEvent, HumanApprovalRequest/Response
│   │
│   ├── config.py            all settings from .env (one import away)
│   └── main.py              FastAPI entry point
│
├── tests/
│   ├── unit/                test individual agents in isolation
│   ├── integration/         test multi-component flows
│   └── e2e/                 full pipeline against a real test repo
│
├── scripts/
│   └── index_repo.py        CLI: index a local repo clone into ChromaDB
│
├── alembic/                 database migrations
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## Setup

**Requirements:** Python 3.12+, Docker Desktop

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/multi-agent-orchestrator
cd multi-agent-orchestrator/backend

# 2. Virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 3. Dependencies
pip install -r requirements-dev.txt

# 4. Environment
cp .env.example .env
# Edit .env — add GROQ_API_KEY and GITHUB_TOKEN (both free)
```

Get your keys:
- **Groq API key** → [console.groq.com](https://console.groq.com) (free, no credit card)
- **GitHub token** → [github.com/settings/tokens](https://github.com/settings/tokens) → Classic → `repo` scope

```bash
# 5. Start
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` — all endpoints are live.

---

## Running the pipeline

### Option 1 — Manual trigger via API

```bash
curl -X POST http://localhost:8000/api/v1/issues/solve \
  -H "Content-Type: application/json" \
  -d '{"repo_full_name": "your-username/your-repo", "issue_number": 1}'
```

### Option 2 — GitHub webhook (automatic)

Point a GitHub webhook at `POST /api/v1/webhooks/github`. Every new issue auto-triggers the pipeline.

For local development, use [ngrok](https://ngrok.com) to expose your local server:

```bash
ngrok http 8000
# Copy the HTTPS URL → GitHub repo Settings → Webhooks → Add webhook
```

### Check job status

```bash
# List all jobs
curl http://localhost:8000/api/v1/jobs

# Get specific job
curl http://localhost:8000/api/v1/jobs/{job_id}

# Approve (when pipeline is paused at human review)
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"job_id": "{job_id}", "decision": "approve"}'
```

---

## Index a repo for RAG

Before the pipeline can search code, the repo needs to be indexed into ChromaDB. Do this once per repo:

```bash
# Clone the target repo somewhere
git clone https://github.com/owner/repo /tmp/target-repo

# Index it
python scripts/index_repo.py owner/repo /tmp/target-repo
# → Indexed 847 code chunks into ChromaDB
```

---

## Key design decisions

**Why LangGraph instead of just chaining functions?**
The retry loop cannot be expressed as a linear chain. When tests fail, we need to go backwards in the pipeline with new information. LangGraph's conditional edges handle this cleanly. The `interrupt()` primitive for human-in-the-loop is also native — no custom state machine needed.

**Why not stream everything to one LLM?**
Context window limits make full-codebase prompting impossible for any real repo. RAG retrieves the 5 most relevant code chunks — the LLM sees exactly what it needs, nothing more. Fix quality is dramatically better than "here is the entire codebase, fix this."

**Why Docker for test execution and not subprocess?**
A language model generating code that runs directly on your machine is a security risk. The Docker sandbox has no network access, memory capped at 512MB, CPU throttled, and gets killed and deleted after every run regardless of outcome. Malicious or broken generated code cannot affect the host.

**Why SQLite for checkpointing and not Redis?**
LangGraph's SQLite checkpointer is zero-config and sufficient for single-node deployment. The entire graph state is serialized after every node. If the server crashes mid-pipeline, the job resumes exactly where it stopped on restart. For multi-node production deployment, swap in the PostgreSQL checkpointer — one line of config.

---

## Observability

Every graph run is traced in [LangSmith](https://smith.langchain.com) (free tier). Each trace shows:
- Per-agent timing and token counts
- Which node triggered a retry and why
- The exact prompt sent to each LLM
- State changes between nodes

```bash
# Add to .env to enable
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=multi-agent-orchestrator
```

Metrics are exposed at `http://localhost:8000/metrics` in Prometheus format.

---

## What this is not

This is not a production-hardened system. It is an engineering demonstration of:

- Multi-agent coordination via a stateful graph
- Practical RAG on a real codebase (not toy examples)
- Safe LLM-generated code execution
- Human-in-the-loop patterns that actually work

The architecture mirrors what AI engineering teams build at scale. The patterns — conditional routing, checkpointing, interrupt gates, per-task model selection — transfer directly to production systems.

---

## License

MIT