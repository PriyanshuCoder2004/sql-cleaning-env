"""
Reward function for the SQL Cleaning Environment.

Design principles:
- Shaped reward: signal at every step, not just end of episode
- Progress reward: proportional to dirty rows cleaned this step
- Efficiency bonus: faster solutions get a small bonus
- Error penalty: SQL errors are penalized but not catastrophically
- No-progress penalty: repeated steps with no improvement are penalized
- Completion bonus: episode-end bonus if task is fully solved
"""


def compute_step_reward(
    dirty_before: int,
    dirty_after: int,
    total_rows: int,
    sql_error: bool,
    step_count: int,
    max_steps: int,
    done: bool,
    grader_score: float = 0.0,
) -> float:
    """
    Compute shaped reward for a single step.

    Returns a float in range [-1.0, 1.0].
    """

    # ── 1. SQL error penalty ─────────────────────────────────────────────────
    if sql_error:
        return -0.15

    if total_rows == 0:
        return 0.0

    # ── 2. Progress reward (main signal) ────────────────────────────────────
    # How many dirty rows were cleaned this step?
    rows_cleaned = max(0, dirty_before - dirty_after)
    progress_fraction = rows_cleaned / total_rows
    progress_reward = progress_fraction * 0.6   # up to +0.6 if all rows cleaned in one step

    # ── 3. Efficiency bonus ──────────────────────────────────────────────────
    # Small bonus for solving with fewer steps used
    steps_remaining = max_steps - step_count
    efficiency_bonus = 0.05 * (steps_remaining / max_steps)

    # ── 4. No-progress penalty ───────────────────────────────────────────────
    # Penalize if the agent made no progress (to discourage no-op loops)
    no_progress_penalty = 0.0
    if rows_cleaned == 0 and step_count > 1:
        no_progress_penalty = -0.05

    # ── 5. Completion bonus (end of episode) ─────────────────────────────────
    completion_bonus = 0.0
    if done and grader_score >= 0.8:
        completion_bonus = 0.3
    elif done and grader_score >= 0.5:
        completion_bonus = 0.1

    # ── 6. Combine ────────────────────────────────────────────────────────────
    total = progress_reward + efficiency_bonus + no_progress_penalty + completion_bonus
    return round(max(-1.0, min(1.0, total)), 4)


def describe_reward(reward: float) -> str:
    """Human-readable explanation of a reward value."""
    if reward >= 0.5:
        return "Excellent progress"
    elif reward >= 0.2:
        return "Good progress"
    elif reward >= 0.05:
        return "Small progress"
    elif reward > 0.0:
        return "Minimal progress"
    elif reward == 0.0:
        return "No change"
    elif reward >= -0.1:
        return "Minor penalty (no progress)"
    else:
        return "Penalty (SQL error)"
