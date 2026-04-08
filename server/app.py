"""
FastAPI server exposing the OpenEnv API for Regulatory Compliance Document Review.

Endpoints:
  POST /reset   — Reset environment (optionally with task_id)
  POST /step    — Execute an action
  GET  /state   — Get full internal state
  GET  /tasks   — List available tasks
  GET  /health  — Health check
  POST /grade   — Grade a completed episode
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
    title="Regulatory Compliance Document Review — OpenEnv",
    description=(
        "An OpenEnv environment simulating regulatory compliance review. "
        "Agents review business documents (contracts, privacy policies, loan applications) "
        "against regulatory rules (GDPR, fair lending, KYC/AML, consumer protection), "
        "flag violations, and produce compliance verdicts."
    ),
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Per-session environment. For hackathon single-user eval this is fine.
# For production, use a session-keyed dict or Redis-backed store.
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
    return {
        "environment": "Regulatory Compliance Document Review",
        "version": "1.0.0",
        "endpoints": ["/health", "/tasks", "/reset", "/step", "/state", "/grade"],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "environment": "compliance-review", "version": "1.0.0"}


@app.get("/tasks")
async def list_tasks():
    tasks = []
    for s in SCENARIOS.values():
        tasks.append(TaskInfo(
            task_id=s.task_id, title=s.title, difficulty=s.difficulty,
            description=s.description, max_steps=s.max_steps,
        ))
    return {"tasks": [t.model_dump() for t in tasks]}


@app.post("/reset")
async def reset(request: ResetRequest = ResetRequest()):
    try:
        observation = _get_env().reset(task_id=request.task_id)
        return {"observation": observation.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
async def step(action: Action):
    try:
        observation, reward, done, info = _get_env().step(action)
        return StepResponse(observation=observation, reward=reward, done=done, info=info).model_dump()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
async def state():
    try:
        s = _get_env().state()
        return s.model_dump()
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


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
