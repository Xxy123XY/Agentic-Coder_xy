# Multi-Agent Orchestrator

An autonomous system that resolves GitHub issues end-to-end — reads the bug report, finds the relevant code, writes a fix, generates tests, runs them in an isolated container, and opens a Pull Request. A human approves before anything ships.

```
GitHub Issue  →  6 agents in a stateful graph  →  Pull Request
```

This isn't a wrapper around an LLM. It's a stateful, fault-tolerant pipeline built on patterns that production AI engineering teams actually use — conditional graph routing, checkpointed retries, human-in-the-loop interrupts, and per-task model selection.

---

## What it actually does

A developer opens issue #42 on a repo: *"Login fails when email contains uppercase letters."*

```
[01]  IssueAnalyzer       reads the issue, extracts:
                          module: auth, severity: high,
                          keywords: ["login", "email", "case-sensitive"]

[02]  CodebaseExplorer    semantic search via embeddings:
                          finds auth/login.js:34-67 (login function)
                          finds utils/email.js:12-28 (comparison helper)

[03]  FixDrafter          generates a unified diff:
                          adds .toLowerCase() before email comparison

[04]  TestWriter          writes test cases covering the fix:
                          uppercase email, mixed case, edge cases

[05]  Validator           runs pylint + mypy on the generated test code,
                          catches syntax errors before wasting Docker time

[06]  Docker Sandbox      pulls the repo, applies the patch, runs the tests
                          in an isolated container with no network access

      <pipeline pauses>   LangGraph interrupt() — state serialized to SQLite,
                          dashboard shows you the diff. You review it.

[07]  PRCreator           if you click Approve:
                          - creates a branch on your repo (or auto-forks
                            for open source projects)
                          - commits the fix and tests
                          - opens a PR titled with the original issue
                          - closes the issue when merged
```

Time from issue open to PR: about 45 seconds. Zero code written by a human between those two events.

---

## Why I built this

I wanted to understand how systems like Devin, Cursor's background agents, and SWE-agent actually work — not at a marketing level, but at the architectural level where retry loops are implemented, where state is checkpointed, where human approval gates live, where models are routed by task.

The answer turned out to be: a stateful graph with conditional edges. Not a chain. Not a sequence of API calls. A graph that can go backwards when tests fail, pause indefinitely when a human is needed, and recover from a server crash mid-pipeline because every node serializes its output before passing control downstream.

This project implements those patterns end-to-end with a free-tier stack.

---

## Architecture

```
                          ┌────────────────────────────────────────────┐
                          │           LangGraph StateGraph              │
                          │                                              │
  GitHub Issue            │   ┌──────────────┐                          │
  (webhook / API) ─────►  │   │IssueAnalyzer │  → llama-3.3-70b         │
                          │   └──────┬───────┘                          │
                          │          │                                   │
                          │   ┌──────▼───────────┐                       │
                          │   │CodebaseExplorer  │  ◄── ChromaDB         │
                          │   │  (RAG search)    │      + embeddings     │
                          │   └──────┬───────────┘                       │
                          │          │                                   │
                          │   ┌──────▼───────┐    retry (max 3)          │
                          │   │ FixDrafter   │ ◄────────────────┐        │
                          │   │ openai/gpt-  │                  │        │
                          │   │ oss-120b     │                  │        │
                          │   └──────┬───────┘                  │        │
                          │          │                          │        │
                          │   ┌──────▼───────┐                  │        │
                          │   │ TestWriter   │                  │        │
                          │   └──────┬───────┘                  │        │
                          │          │                          │        │
                          │   ┌──────▼───────┐ fail ────────────┘        │
                          │   │  Validator   │                           │
                          │   │ pylint+mypy  │                           │
                          │   └──────┬───────┘                           │
                          │          │ pass                              │
                          │   ┌──────▼───────┐ fail ────────────────────►│
                          │   │   Docker     │
                          │   │   Sandbox    │
                          │   │   (pytest)   │
                          │   └──────┬───────┘
                          │          │ pass
                          │   ┌──────▼───────┐
                          │   │   Human      │  ◄── interrupt()
                          │   │   Review     │      pipeline pauses here
                          │   └──────┬───────┘      state in SQLite
                          │          │ approved
                          │   ┌──────▼───────┐
                          │   │  PRCreator   │  ──► fork if no write access
                          │   └──────┬───────┘
                          └──────────┼─────────────────────────────────┘
                                     │
                                     ▼
                              Pull Request
```

The retry loop is the most important detail. When Validator finds type errors or the sandbox tests fail, the graph routes back to FixDrafter with the failure output attached to state. The next attempt is smarter because it has seen what went wrong. This is not infinite retry — `retry_count` is tracked in state, hard cap at 3.

The `interrupt()` before PRCreator is non-negotiable. LangGraph pauses the graph mid-execution, serializes the entire state to SQLite, and waits for an HTTP call to resume. You review the diff in the dashboard. Approve → PR opens. Reject → pipeline ends.

---

## Tech stack and why

Every choice here was made deliberately. Free tier where possible, open source everywhere else.

| Layer | Tool | Why this and not the alternative |
|---|---|---|
| Orchestration | LangGraph | Stateful graphs with conditional edges and checkpointing. Not LangChain chains — chains can't loop, retry, or pause for humans. |
| LLM (reasoning) | Groq `llama-3.3-70b-versatile` | Free tier, ~300 tokens/sec. No local GPU needed. |
| LLM (code) | Groq `openai/gpt-oss-120b` | Specialized for code generation. The original choice (`qwen-2.5-coder-32b`) was decommissioned by Groq mid-project. |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | 80MB, CPU-only, no API key. Considered OpenAI embeddings — would cost real money on a free-tier project. |
| Vector DB | ChromaDB | Local persistent store, single Python import, zero infrastructure. Considered Pinecone (free tier exists but rate-limited), Weaviate (overkill). |
| Code chunking | tree-sitter | Splits at function and class boundaries by parsing the actual AST. Line-based splitters destroy semantic context. |
| Code execution | Docker + docker-py | Network disabled, memory capped at 512MB, CPU throttled, killed and removed after every run. A subprocess approach would let model-generated code touch the host. |
| API | FastAPI | Async-native, auto-generates OpenAPI docs, Pydantic integration for free. |
| State persistence | SQLite via `langgraph-checkpoint-sqlite` | Crash recovery — server restart mid-pipeline resumes from the last checkpoint. Considered MongoDB; the LangGraph checkpointer wants SQLite anyway. |
| GitHub | PyGithub | Full repo access, PR creation, fork management. |
| Frontend | React + Vite | Familiar from MERN experience. Vite over CRA (CRA is deprecated). |
| DAG visualization | react-flow | Interactive node graphs with built-in pan, zoom, smooth edges. |
| Logging | structlog | JSON in production, pretty console in development. Every log line tagged with `job_id`, `agent_name`, duration. |

**Total infrastructure cost: $0.** No OpenAI bill, no paid vector DB, no cloud GPU, no managed checkpoint store.

---

## Project structure

```
multi-agent-orchestrator/
│
├── backend/                              FastAPI + LangGraph orchestrator
│   ├── app/
│   │   ├── agents/                       6 agents, one file each
│   │   │   ├── base.py                   abstract class — logging + error handling
│   │   │   ├── issue_analyzer.py         GitHub issue → structured JSON
│   │   │   ├── codebase_explorer.py      RAG search → top 5 relevant chunks
│   │   │   ├── fix_drafter.py            issue + code context → unified diff
│   │   │   ├── test_writer.py            diff → pytest test cases
│   │   │   ├── validator.py              static analysis (pylint + mypy)
│   │   │   └── pr_creator.py             branch + commit + PR (fork-aware)
│   │   │
│   │   ├── graph/
│   │   │   ├── state.py                  TypedDict — shared state contract
│   │   │   ├── builder.py                StateGraph: nodes + edges in one place
│   │   │   ├── edges.py                  conditional routing (retry/pass/fail)
│   │   │   └── checkpointer.py           SQLite persistence wrapper
│   │   │
│   │   ├── rag/
│   │   │   ├── chunker.py                tree-sitter AST-based chunking
│   │   │   ├── embedder.py               sentence-transformers wrapper
│   │   │   ├── vector_store.py           ChromaDB index + search
│   │   │   └── retriever.py              high-level API used by agents
│   │   │
│   │   ├── sandbox/
│   │   │   ├── executor.py               Docker container lifecycle
│   │   │   ├── runner.py                 pytest workflow + diff application
│   │   │   └── parser.py                 pytest stdout → structured results
│   │   │
│   │   ├── github/
│   │   │   ├── client.py                 PyGithub singleton
│   │   │   ├── webhook.py                HMAC-SHA256 signature verification
│   │   │   └── pr.py                     branch + commit + PR (fork detection)
│   │   │
│   │   ├── llm/
│   │   │   ├── router.py                 picks model by task (reasoning vs code)
│   │   │   └── groq_client.py            async Groq wrapper with retry
│   │   │
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── issues.py             POST /api/v1/issues/solve
│   │   │   │   ├── jobs.py               GET /jobs, POST /jobs/{id}/approve
│   │   │   │   └── webhooks.py           POST /webhooks/github
│   │   │   └── websocket.py              WS /ws/jobs/{id} — live event stream
│   │   │
│   │   ├── db/                           SQLAlchemy + async session
│   │   ├── schemas/                      Pydantic models
│   │   ├── observability/                structlog + Prometheus metrics
│   │   ├── config.py                     Settings via pydantic-settings
│   │   └── main.py                       FastAPI entry point
│   │
│   ├── infra/sandbox/Dockerfile          pre-built sandbox image with pytest
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                             React dashboard
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx             jobs list + solve form + stats
│   │   │   └── JobDetail.jsx             DAG + diff + approval panel
│   │   ├── components/
│   │   │   ├── PipelineDag.jsx           react-flow visualization
│   │   │   ├── DiffViewer.jsx            colored unified diff
│   │   │   ├── ApprovalPanel.jsx         approve / reject UI
│   │   │   ├── SolveIssueForm.jsx        accepts owner/repo or full URL
│   │   │   ├── JobCard.jsx               status pill + timestamps
│   │   │   ├── StatusBadge.jsx           color-coded job status
│   │   │   └── EventLog.jsx              live agent events
│   │   ├── lib/
│   │   │   ├── api.js                    axios wrapper for backend
│   │   │   ├── websocket.js              WS hook for live updates
│   │   │   └── utils.js                  date / format helpers
│   │   ├── App.jsx                       router + header
│   │   └── main.jsx                      Vite entry
│   ├── vite.config.js
│   └── package.json
│
└── README.md
```

---

## Setup

**Requirements:** Python 3.12, Node.js 18+, Docker Desktop running.

```bash
git clone https://github.com/Iam-raunac/multi-agent-orchestrator
cd multi-agent-orchestrator
```

### Backend

```bash
cd backend

python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — add GROQ_API_KEY and GITHUB_TOKEN (both free)
```

Get your keys:
- **Groq** → [console.groq.com](https://console.groq.com) — free, no credit card
- **GitHub** → [github.com/settings/tokens](https://github.com/settings/tokens) → Classic token with `repo` scope

Build the sandbox image (one time):

```bash
cd infra/sandbox
docker build -t sandbox-runner:latest .
cd ../..
```

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` — interactive API documentation.

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

---

## Running the pipeline

### Through the dashboard

1. Open `http://localhost:5173`
2. Paste a repo (either `owner/repo` or a full GitHub URL)
3. Enter an issue number
4. Click **Run Pipeline**
5. Watch the agents run in real-time on the detail page
6. When the pipeline pauses for review, inspect the diff and click **Approve**
7. PR URL appears at the top of the page

### Through the API directly

```bash
curl -X POST http://localhost:8000/api/v1/issues/solve \
  -H "Content-Type: application/json" \
  -d '{"repo_full_name": "Iam-raunac/bug_test", "issue_number": 1}'
```

Returns a job ID. Poll for status:

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

When status is `awaiting_review`, approve:

```bash
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"job_id": "{job_id}", "decision": "approve"}'
```

### Indexing a repo for RAG

Before the pipeline can search code, the target repo needs to be in ChromaDB:

```bash
git clone https://github.com/owner/repo /tmp/target-repo

python -c "
from app.rag.retriever import retriever
count = retriever.index_repo('owner/repo', '/tmp/target-repo')
print(f'Indexed {count} chunks')
"
```



## Key design decisions

Some of these were learned the hard way. Worth documenting honestly.

**Why LangGraph and not a chain of function calls.** The retry loop cannot be expressed as a linear sequence. When tests fail, the next step is not "next" — it's "back to FixDrafter with failure output attached." LangGraph's conditional edges handle this cleanly. `interrupt()` for human-in-the-loop is also native — no custom state machine needed.

**Why RAG and not "dump the whole codebase into the prompt."** Context window limits make full-codebase prompting impossible for any real repo. Even when it fits, fix quality is worse — the model gets distracted by irrelevant code. RAG retrieves the 5 most relevant chunks based on embedding similarity to the issue keywords. The model sees exactly what it needs.

**Why Docker for test execution and not subprocess.** A language model generating code that runs directly on your machine is a security risk. The Docker sandbox has no network access, memory capped, CPU throttled, and gets killed and deleted after every run regardless of outcome. Even if the model generated `rm -rf /`, the host is untouched.

**Why SQLite for checkpointing and not Redis.** LangGraph's SQLite checkpointer is zero-config and sufficient for single-node deployment. Every node's output is serialized to disk before control passes to the next node. Server crash mid-pipeline? Resume from the last checkpoint on restart. For multi-node production deployment, swap in the PostgreSQL checkpointer — one config line.

**Why FastAPI background tasks for the approval endpoint.** Initially I had `approve_job` run the graph resume synchronously inside the request handler. This worked in standalone scripts but consistently failed inside FastAPI — the long-running graph operation interacted badly with the held DB session from `Depends(get_db)`. Moved the graph resume into a background task with its own fresh DB session. Same pattern as the initial pipeline run. Solved immediately.

**Why timestamp suffixes on branch names.** First few demo runs created `fix/issue-1` branches that conflicted on the second attempt (`422 Reference already exists`). Now every branch is `fix/issue-{number}-{YYYYMMDDhhmmss}`. Idempotent, ugly, works.

**Why pre-built sandbox image instead of `pip install` at runtime.** With `network_disabled=True` on the container (security requirement), `pip install pytest` inside the container can't reach PyPI. Pre-built a custom `sandbox-runner:latest` image with pytest already installed. Network can stay disabled, tests can still run.

**Why markdown fence stripping is its own helper.** LLMs wrap code in triple backticks even when explicitly told not to. Built a `_strip_fences()` helper into both `fix_drafter.py` and `test_writer.py`. Five-line function, saves hours of debugging "why is my diff malformed."

**Why no MCP server.** Model Context Protocol is excellent when multiple LLM clients need to share tools — Claude Desktop, Cursor, custom apps, all hitting the same `search_codebase` tool. This project is a single closed system. Adding MCP would introduce JSON-RPC serialization on every tool call without any cross-client benefit. The architectural value of MCP is interoperability, which isn't a requirement here.

---

## Known limitations

This project is portfolio-grade, not production-hardened. Honest list of things that don't work well yet:

- **Language awareness in TestWriter.** Currently generates Python pytest tests regardless of target codebase language. Fine for Python repos, broken for JavaScript repos (the generated `import` statements fail). Fix is to detect target language from indexed file extensions and route to a language-appropriate test template.
- **No SWE-bench evaluation yet.** All testing is on hand-crafted issues in a controlled repo. Running this against the SWE-bench dataset would give a real success rate.
- **Webhook signature verification skipped in dev.** When `GITHUB_WEBHOOK_SECRET` is empty, the webhook endpoint accepts everything. Fine for development, dangerous in production.
- **Single-node only.** SQLite checkpointer doesn't scale horizontally. PostgreSQL swap is documented but not implemented.
- **No frontend authentication.** Anyone with the URL can trigger jobs and approve PRs. Fine for local-only demo, not for public deployment.
- **Retry budget is per-pipeline, not per-issue.** A repo with consistently failing tests will burn 3 retries every time the same issue is re-triggered.

---

## What this isn't

It isn't Devin. It doesn't long-run on complex multi-day tasks, it doesn't handle ambiguous requirements through clarifying questions, it doesn't manage its own development environment.

It is a demonstration of the architectural patterns that make autonomous engineering systems work — patterns I learned by reading papers about SWE-agent, studying Cognition's blog posts, and then implementing them with the cheapest possible infrastructure.

The patterns transfer. Conditional graph routing, retry loops with failure context, checkpoint-based crash recovery, human-in-the-loop interrupts, per-task model selection, AST-aware code chunking, sandboxed test execution — these are the same primitives used by production AI engineering systems. The implementations might be smaller here, but the architecture is the same shape.

---



If you build on this, I'd love to hear what you made.
