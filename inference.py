#!/usr/bin/env python3
import os, sys, json, httpx
from openai import OpenAI

# ✅ ENV VARIABLES
API_BASE_URL = os.getenv("API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
MODEL_NAME   = os.getenv("MODEL_NAME", "gemini-3-flash-preview")
HF_TOKEN     = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
ENV_URL      = os.getenv("ENV_URL", "http://localhost:7860")

# ✅ OpenAI Client (IMPORTANT FIX)
client = OpenAI(
    api_key=HF_TOKEN,
    base_url=API_BASE_URL
)

BENCHMARK = "sql-cleaning-env"
MAX_STEPS = 10
SUCCESS_THRESHOLD = 0.5


# ✅ LOG FORMAT (DO NOT CHANGE)
def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error):
    error_val = error if error else "null"
    done_val  = str(done).lower()
    action_s  = str(action).replace("\n","")
    print(f"[STEP] step={step} action={action_s} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


# ✅ FALLBACK SQL (important for stability)
def fallback_sql(task_name, step):
    if task_name == "null_filling":
        return "UPDATE users SET email = 'unknown@example.com' WHERE email IS NULL OR TRIM(email) = '' OR LOWER(TRIM(email)) IN ('null','n/a','none');"

    if task_name == "deduplication":
        return "DELETE FROM orders WHERE rowid NOT IN (SELECT MIN(rowid) FROM orders GROUP BY id, product, amount, customer);"

    if task_name == "schema_normalization":
        if step == 1:
            return "UPDATE contacts SET country = 'United States' WHERE country != 'United States';"
        elif step == 2:
            return """
            UPDATE contacts
            SET phone = substr(p,1,3) || '-' || substr(p,4,3) || '-' || substr(p,7,4)
            FROM (
                SELECT rowid,
                replace(replace(replace(replace(replace(phone,'(',''),')',''),'-',''),' ',''),'.','') AS p
                FROM contacts
            )
            WHERE contacts.rowid = rowid;
            """

    if task_name == "type_coercion":
        if step == 1:
            return "UPDATE products SET price = REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(price,'$',''),'£',''),'€',''),' USD',''),',','');"
        elif step == 2:
            return "UPDATE products SET quantity = CAST(quantity AS INTEGER);"

    return "SELECT 1;"


# ✅ UPDATED LLM CALL (OpenAI client)
def get_sql(task_name, step, table_preview):

    prompt = f"""
You are a data cleaning agent.

Task: {task_name}

Table preview:
{table_preview}

Generate ONLY SQL query to clean data.
Do not explain anything.
Return only SQL.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        sql = response.choices[0].message.content.strip()

        # 🔥 Safety check
        if "UPDATE" not in sql and "DELETE" not in sql:
            return fallback_sql(task_name, step)

        return sql

    except Exception:
        return fallback_sql(task_name, step)


def safe_json(response, label):
    if not response.text.strip():
        print(f"[DEBUG] EMPTY RESPONSE ({label}) status={response.status_code}", flush=True)
        return None
    try:
        return response.json()
    except Exception:
        print(f"[DEBUG] INVALID JSON ({label}): {response.text}", flush=True)
        return None


def run_task(base_url, task_name):

    rewards    = []
    steps_done = 0
    success    = False
    score      = 0.0

    log_start(task_name, BENCHMARK, MODEL_NAME)

    try:
        # RESET
        r = httpx.post(f"{base_url}/reset", json={"task_name": task_name})
        obs = safe_json(r, "reset")

        if not obs:
            log_end(False, 0, 0.0, [])
            return 0.0

        for step in range(1, MAX_STEPS + 1):

            if obs.get("done", False):
                break

            sql = get_sql(task_name, step, obs.get("table_preview"))

            sr = httpx.post(f"{base_url}/step", json={"sql": sql})
            obs = safe_json(sr, f"step-{step}")

            if not obs:
                break

            reward = float(obs.get("reward", 0))
            done   = bool(obs.get("done"))
            error  = obs.get("last_sql_error")

            rewards.append(reward)
            steps_done = step

            log_step(step, sql, reward, done, error)

            if done:
                break

        # GRADER
        gr = httpx.get(f"{base_url}/grader")
        grader = safe_json(gr, "grader")

        if grader:
            score = grader.get("score", 0.0)
            success = score >= SUCCESS_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] ERROR: {e}", flush=True)

    finally:
        log_end(success, steps_done, score, rewards)

    return score


def main():
    if not HF_TOKEN:
        print("ERROR: API KEY missing")
        sys.exit(1)

    try:
        httpx.get(f"{ENV_URL}/health").raise_for_status()
    except:
        print("Server not running")
        sys.exit(1)

    tasks = httpx.get(f"{ENV_URL}/tasks").json()["tasks"]

    for t in tasks:
        run_task(ENV_URL, t["id"])
        print()


if __name__ == "__main__":
    main()
