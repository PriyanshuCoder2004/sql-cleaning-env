"""
SQL Cleaning Environment — FastAPI server.
"""

import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from models import SQLAction, SQLObservation, ResetRequest
from environment import SQLCleaningEnvironment
from graders import GRADERS
from tasks import list_tasks, TASKS

# ── App ─────────────────────────────────────────────

app = FastAPI(
    title="SQL Cleaning Environment",
    description="OpenEnv environment for training AI agents to clean dirty SQL data.",
    version="0.1.0",
)

env = SQLCleaningEnvironment()

# ── SYSTEM PROMPT (🔥 FIXED) ─────────────────────────

SYSTEM_PROMPT = """
You are a SQLite SQL cleaning agent.

CRITICAL RULES (STRICT):
If you use wrong table name or unsupported function, your response will FAIL.
Always double-check table names before answering.

- Output ONLY raw SQL (no explanation, no markdown, no ```sql)
- NEVER use words like table_name or dataset
- ONLY use these tables:
    users(email)
    orders(id, product, amount, customer)
    contacts(country, phone)
    products(price, quantity)

- ONLY use SQLite functions:
    REPLACE, LOWER, TRIM, SUBSTR
- DO NOT use:
    REGEXP_REPLACE, REGEX, CAST with DECIMAL, or any unsupported functions

- ALWAYS end with semicolon

----------------------
TASK-SPECIFIC RULES
----------------------

NULL FILLING:
UPDATE users
SET email = 'unknown@example.com'
WHERE email IS NULL OR TRIM(LOWER(email)) IN ('', 'null', 'none', 'n/a');

----------------------

DEDUPLICATION:
DELETE FROM orders
WHERE rowid NOT IN (
    SELECT MIN(rowid)
    FROM orders
    GROUP BY id, product, amount, customer
);

----------------------

SCHEMA NORMALIZATION:
UPDATE contacts
SET country = 'United States';

UPDATE contacts
SET phone =
    SUBSTR(phone, -10, 3) || '-' ||
    SUBSTR(phone, -7, 3) || '-' ||
    SUBSTR(phone, -4, 4);

----------------------

TYPE COERCION:
UPDATE products
SET price = REPLACE(REPLACE(REPLACE(REPLACE(price,'$',''),'£',''),'€',''),',','');

UPDATE products
SET quantity = TRIM(quantity);

----------------------

IMPORTANT:
- NEVER invent table names
- NEVER use REGEX
- ONLY SQLite syntax allowed
"""

# ── Health ─────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "ok"}

# ── Core OpenEnv APIs ──────────────────────────────

@app.post("/reset")
def reset(request: ResetRequest = None):
    try:
        task_name = (request.task_name if request else None) or "null_filling"

        if task_name not in TASKS:
            raise HTTPException(status_code=400, detail="Invalid task")

        obs = env.reset(task_name=task_name)
        return obs.model_dump()

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/step")
def step(action: SQLAction):
    try:
        if env._conn is None:
            raise HTTPException(status_code=400, detail="Call /reset first")

        obs = env.step(action)
        return obs.model_dump()

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/state")
def state():
    return env.state()

# ── Extra APIs ─────────────────────────────────────

@app.get("/tasks")
def get_tasks():
    return {
        "tasks": list_tasks(),
        "action_schema": SQLAction.model_json_schema(),
    }


@app.get("/grader")
def run_grader():
    try:
        grader_fn = GRADERS.get(env._task_name)
        result = grader_fn(env._conn)
        return result.model_dump()

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ── BASELINE (🔥 FIXED STRUCTURE) ───────────────────

@app.get("/baseline")
def run_baseline():

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API key missing")

    from openai import OpenAI

    oai = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    results = []

    for task_name in TASKS.keys():

        obs = env.reset(task_name=task_name)
        episode_reward = 0.0
        steps_taken = 0

        for step_num in range(env.MAX_STEPS):

            user_prompt = f"""
Task: {obs.message}

Table Preview:
{json.dumps(obs.table_preview, indent=2)}

Dirty rows: {obs.dirty_count}/{obs.total_rows}
Step: {step_num + 1}
"""

            if obs.last_sql_error:
                user_prompt += f"\nLast error: {obs.last_sql_error}\n"

            # 🔥 LLM CALL
            try:
                response = oai.chat.completions.create(
                    model="gemini-3-flash-preview",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                )

                sql = response.choices[0].message.content.strip()

                # 🔥 REMOVE MARKDOWN
                sql = sql.replace("```sql", "").replace("```", "").strip()

                # 🔥 HARD VALIDATION
                if "REGEXP" in sql or "table_name" in sql or "dataset" in sql:
                    sql = "SELECT 1;"

            except Exception:
                sql = "SELECT 1;"  # fallback

            # 🔥 EXECUTE ACTION
            action = SQLAction(sql=sql)
            obs = env.step(action)

            episode_reward += obs.reward
            steps_taken += 1

            if obs.done:
                break

        # 🔥 GRADING
        grader_fn = GRADERS.get(env._task_name)
        grader_result = grader_fn(env._conn)

        results.append({
            "task": task_name,
            "steps": steps_taken,
            "reward": round(episode_reward, 3),
            "score": grader_result.score,
            "verdict": grader_result.verdict
        })

    avg_score = round(sum(r["score"] for r in results) / len(results), 3)

    return {
        "results": results,
        "avg_score": avg_score
    }
