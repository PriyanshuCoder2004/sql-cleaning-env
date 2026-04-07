from pydantic import BaseModel, Field
from typing import Optional, List, Any


class SQLAction(BaseModel):
    """Action the agent takes: one or more SQL statements."""
    sql: str = Field(..., description="SQL statement(s) to execute. Separate multiple with semicolons.")
    reasoning: Optional[str] = Field(None, description="Optional explanation of the agent's approach.")


class SQLObservation(BaseModel):
    """What the agent observes after each step."""
    table_preview: List[dict] = Field(..., description="First 10 rows of the current table state.")
    dirty_count: int = Field(..., description="Number of remaining dirty/invalid records.")
    total_rows: int = Field(..., description="Total rows in the table.")
    last_sql_error: Optional[str] = Field(None, description="SQL error from the last step, if any.")
    done: bool = Field(default=False, description="Whether the episode has ended.")
    reward: float = Field(default=0.0, description="Reward received for this step.")
    message: str = Field(default="", description="Task description and current status.")
    step_count: int = Field(default=0, description="Current step number in the episode.")


class GraderResult(BaseModel):
    """Result from the automated grader."""
    score: float = Field(..., ge=0.0, le=1.0, description="Score between 0.0 and 1.0.")
    breakdown: dict = Field(..., description="Detailed breakdown of how the score was computed.")
    verdict: str = Field(..., description="PASS / PARTIAL / FAIL")
    task_name: str = Field(default="", description="Name of the task that was graded.")
    details: str = Field(default="", description="Human-readable explanation of the result.")


class TaskInfo(BaseModel):
    """Metadata about a single task."""
    id: str
    name: str
    difficulty: str
    description: str
    max_steps: int
    passing_threshold: float


class ResetRequest(BaseModel):
    """Request body for the /reset endpoint."""
    task_name: str = Field(default="null_filling", description="Which task to start. One of: null_filling, deduplication, schema_normalization, type_coercion.")
