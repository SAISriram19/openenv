"""
OpenEnv-compatible wrapper for the Compliance Review Environment.
Extends openenv.core.env_server.interfaces.Environment.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
from uuid import uuid4

try:
    from openenv.core.env_server.interfaces import Environment
    from openenv.core.env_server.types import State
except ImportError:
    # Fallback if openenv not installed
    class Environment:
        pass
    class State:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

from env.environment import ComplianceReviewEnv
from env.graders import grade_episode
from env.models import Action, Observation, Reward
from env.scenarios import SCENARIOS


class ComplianceReviewEnvironment(Environment):
    """OpenEnv-compatible compliance review environment."""

    def __init__(self):
        self._env = ComplianceReviewEnv()
        self._current_task = "easy_privacy_review"
        self._episode_id = str(uuid4())

    def reset(self, seed=None, options=None) -> Observation:
        if options and isinstance(options, dict):
            task_id = options.get("task_id", self._current_task)
        elif seed is not None and isinstance(seed, str):
            task_id = seed
        else:
            task_id = self._current_task
        self._current_task = task_id
        self._episode_id = str(uuid4())
        return self._env.reset(task_id)

    def step(self, action) -> tuple:
        if isinstance(action, dict):
            action = Action(**action)
        elif isinstance(action, Action):
            pass
        else:
            action = Action(action_type="noop")
        obs, reward, done, info = self._env.step(action)
        return obs, reward.total if hasattr(reward, 'total') else reward, done, info

    @property
    def state(self):
        return self._env.state()

    def close(self):
        pass
