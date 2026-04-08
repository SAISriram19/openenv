"""
FastAPI application for the Regulatory Compliance Document Review Environment.
"""
from __future__ import annotations
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from env.environment import ComplianceReviewEnv
from env.graders import grade_episode
from env.models import Action, EnvironmentState, Observation, Reward
from env.scenarios import SCENARIOS


app = FastAPI(
    title="Regulatory Compliance Document Review",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_envs: Dict[str, ComplianceReviewEnv] = {}

def _get_env(session_id: str = "default") -> ComplianceReviewEnv:
    if session_id not in _envs:
        _envs[session_id] = ComplianceReviewEnv()
    return _envs[session_id]


class ResetRequest(BaseModel):
    task_id: Optional[str] = "easy_privacy_review"

class StepResponse(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: Dict[str, Any]

class GradeResponse(BaseModel):
    task_id: str
    score: float
    details: Dict[str, Any]

class TaskInfo(BaseModel):
    task_id: str
    title: str
    difficulty: str
    description: str
    max_steps: int


@app.get("/")
async def root():
    return {"environment": "Regulatory Compliance Document Review", "version": "1.0.0",
            "endpoints": ["/health", "/tasks", "/reset", "/step", "/state", "/grade"]}

@app.get("/health")
async def health():
    return {"status": "ok", "environment": "compliance-review", "version": "1.0.0"}


@app.get("/tasks")
async def list_tasks():
    tasks = []
    for tid, sc in SCENARIOS.items():
        tasks.append(TaskInfo(task_id=tid, title=sc.title, difficulty=sc.difficulty,
                              description=sc.description, max_steps=sc.max_steps).model_dump())
    return {"tasks": tasks}

@app.post("/reset")
async def reset(req: ResetRequest = None):
    task_id = req.task_id if req else "easy_privacy_review"
    try:
        env = _get_env()
        obs = env.reset(task_id)
        return {"observation": obs.model_dump()}
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/step")
async def step(action: Dict[str, Any]):
    try:
        a = Action(**action)
        obs, reward, done, info = _get_env().step(a)
        return {"observation": obs.model_dump(), "reward": reward.model_dump(), "done": done, "info": info}
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
async def state():
    try:
        return _get_env().state().model_dump()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/grade")
async def grade():
    try:
        s = _get_env().state()
        score = grade_episode(s)
        return GradeResponse(
            task_id=s.task_id, score=score,
            details={
                "step_number": s.step_number, "max_steps": s.max_steps,
                "done": s.done, "review_submitted": s.review_submitted,
                "overall_status": s.overall_status,
                "ground_truth_violations": s.ground_truth_violations,
                "detected_correctly": s.detected_correctly,
                "false_positives": s.false_positives,
                "missed_violations": s.missed_violations,
                "cumulative_reward": s.cumulative_reward,
            },
        ).model_dump()
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


def main(host: str = "0.0.0.0", port: int = 7860):
    """Entry point for running server via uv run or python -m."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
