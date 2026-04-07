---
title: SQL Cleaning Environment
emoji: 🧹
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
tags:
  - openenv
  - data-cleaning
  - sql
  - reinforcement-learning
---

# SQL Cleaning Environment

An **OpenEnv-compatible reinforcement learning environment** where AI agents learn
to clean dirty SQL databases. Agents issue SQL `UPDATE` / `DELETE` statements
and receive shaped rewards for progressive data quality improvement.

Every data team in the world runs SQL cleaning pipelines. Dirty data costs
organisations millions annually. This environment provides a principled,
fully automated benchmark for evaluating agents on the four most common
real-world SQL cleaning operations — with **100% deterministic graders**
(no LLM-as-judge, no subjectivity).

---

## Environment description

The agent interacts with an in-memory SQLite database. Each episode:
1. `reset()` creates a fresh dirty table
2. The agent calls `step(sql)` to execute SQL statements
3. The grader measures how much of the data has been cleaned
4. The episode ends when the table is fully clean OR max steps is reached

---

## Action space

```json
{
  "sql": "UPDATE users SET email = 'unknown@example.com' WHERE email IS NULL",
  "reasoning": "Fill all null emails with placeholder (optional field)"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sql` | string | Yes | SQL statement(s) to execute. Separate multiple with `;` |
| `reasoning` | string | No | Optional explanation (not executed) |

---

## Observation space

```json
{
  "table_preview": [{"id": 1, "name": "Alice", "email": null}],
  "dirty_count": 3,
  "total_rows": 7,
  "last_sql_error": null,
  "done": false,
  "reward": 0.34,
  "message": "Task: Fill NULL emails...",
  "step_count": 1
}
```

| Field | Type | Description |
|-------|------|-------------|
| `table_preview` | array | First 10 rows of the current table |
| `dirty_count` | int | Remaining dirty/invalid records |
| `total_rows` | int | Total rows in the table |
| `last_sql_error` | string\|null | Error from last step if SQL was invalid |
| `done` | bool | Whether the episode has ended |
| `reward` | float | Shaped reward for this step (-1.0 to 1.0) |
| `message` | string | Task description + current status |
| `step_count` | int | Steps taken so far |

---

## Tasks

| Task | Difficulty | Table | Description |
|------|-----------|-------|-------------|
| `null_filling` | Easy | `users` | Fill NULL email values with `'unknown@example.com'` |
| `deduplication` | Medium | `orders` | Remove exact duplicate rows, keep one of each |
| `schema_normalization` | Hard | `contacts` | Normalize country (`'US'` → `'United States'`) and phone (`'5551234567'` → `'555-123-4567'`) formats |
| `type_coercion` | Hard | `products` | Convert messy prices (`'$9.99'`, `'10,000'`) and quantities (`'3 units'`, `'12pcs'`) to clean numbers |

---

## Reward function

The reward is **shaped** — the agent receives signal at every step, not just at episode end.

| Component | Value | Condition |
|-----------|-------|-----------|
| Progress reward | `+0.6 × (rows_cleaned / total_rows)` | Rows cleaned this step |
| Efficiency bonus | `+0.05 × (steps_remaining / max_steps)` | Every step |
| No-progress penalty | `-0.05` | No rows cleaned after step 1 |
| SQL error penalty | `-0.15` | Invalid SQL syntax |
| Completion bonus | `+0.30` | Episode ends with grader score ≥ 0.8 |
| Completion bonus (partial) | `+0.10` | Episode ends with grader score ≥ 0.5 |

Range: **-1.0 to +1.0**

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/reset` | Start new episode. Body: `{"task_name": "null_filling"}` |
| `POST` | `/step` | Execute SQL action. Body: `{"sql": "UPDATE ..."}` |
| `GET` | `/state` | Current episode metadata |
| `GET` | `/tasks` | List all tasks + action schema |
| `GET` | `/grader` | Score the current episode (0.0–1.0) |
| `GET` | `/baseline` | Run Gemini 2.0 Flash on all tasks, return scores |
| `GET` | `/health` | Health check |

---

## BASELINE RESULTS SUMMARY (gemini-3-flash-preview)

| Task | Difficulty | Grader Score | Verdict | Steps |
|------|-----------|-------------|---------|-------|
| `null_filling` | Easy | 1.000 | PASS | 2 |
| `deduplication` | Medium | 1.000 | PASS | 1 |
| `schema_normalization` | Hard | 1.000 | PASS | 4 |
| `type_coercion` | Hard | 1.000 | PASS | 6 |
| **Average** | | **1.000** | | |

---

## Setup and usage

### Local development

```bash
# 1. Clone the repo
git clone https://github.com/your-username/sql-cleaning-env
cd sql-cleaning-env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn app:app --host 0.0.0.0 --port 7860

# 4. Test endpoints (in another terminal)
curl http://localhost:7860/health
curl http://localhost:7860/tasks
curl -X POST http://localhost:7860/reset \
     -H "Content-Type: application/json" \
     -d '{"task_name": "null_filling"}'

# 5. Run baseline (requires Gemini API key from aistudio.google.com)
export OPENAI_API_KEY=AIza-your-gemini-key
python baseline_inference.py
```

### Docker

```bash
# Build
docker build -t sql-cleaning-env .

# Run
docker run -p 7860:7860 -e OPENAI_API_KEY=AIza-your-gemini-key sql-cleaning-env

# Test
curl http://localhost:7860/health
```

### Hugging Face Spaces

The environment is deployed at:
`https://huggingface.co/spaces/PriyanshuCoder/sql-cleaning-env`

---

## Project structure

```

sql-cleaning-env/
├── files/
│   ├── __pycache__/
│   ├── app.py              ← FastAPI server (all endpoints)
│   ├── Dockerfile          ← Port 7860, python:3.11-slim
│   ├── environment.py      ← Core RL env: step() / reset() / state()
│   ├── graders.py          ← 4 deterministic graders (0.0–1.0 scores)
│   ├── inference.py        ← Standalone baseline script
│   ├── models.py           ← Pydantic models: SQLAction, SQLObservation, GraderResult
│   ├── openenv.yaml        ← OpenEnv spec metadata
│   ├── README.md
│   ├── requirements.txt    
│   ├── rewards.py          ← Shaped reward function
│   └── tasks.py            ← 4 task definitions with setup SQL
│
├── venv/
│   ├── Include/
│   ├── Lib/
│   └── Scripts/
│
├── .gitignore
└── pyvenv.cfg

```
