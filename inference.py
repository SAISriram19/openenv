"""
Inference Script -- Regulatory Compliance Document Review OpenEnv
Optimized for <25 minute runtime on 2 vCPU / 8GB RAM.
"""

import json, os, re, time
from typing import Any, Dict, List
import requests
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN", "")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
BENCHMARK = "compliance_review"
TOTAL_TIMEOUT = 1500  # 25 min hard cap
MAX_STEPS_PER_TASK = 12
MAX_TOKENS = 400
TEMPERATURE = 0.1

SYSTEM = """You are a compliance analyst. Return ONE JSON action per turn. No markdown.
Actions: read_regulation, flag_violation, flag_compliant, submit_review.
Format: {"action_type":"...", "target":"...", "parameters":{...}}
flag_violation needs: section, regulation, severity (critical/major), confidence (0-1), description.
submit_review needs: overall_status (non_compliant/compliant), risk_score (1-10), summary."""


class Env:
    def __init__(self, url):
        self.url = url.rstrip("/")
        self.s = requests.Session()
    def health(self): return self.s.get(f"{self.url}/health", timeout=10).json()
    def reset(self, tid): return self.s.post(f"{self.url}/reset", json={"task_id": tid}, timeout=10).json()
    def step(self, a): return self.s.post(f"{self.url}/step", json=a, timeout=10).json()
    def grade(self): return self.s.post(f"{self.url}/grade", timeout=10).json()
    def tasks(self): return self.s.get(f"{self.url}/tasks", timeout=10).json()["tasks"]


def build_prompt(obs, step, max_steps):
    """Single-turn prompt -- no message accumulation."""
    rem = max_steps - step
    parts = [f"STEP {step}/{max_steps} ({rem} left)."]
    if rem <= 2:
        parts.append("URGENT: submit_review NOW.")
    parts.append(obs.get("task_description", "")[:800])
    for doc in obs.get("documents", [])[:2]:
        parts.append(f"DOC {doc['doc_id']}: {doc.get('summary','')[:400]}")
    ar = obs.get("action_result")
    if ar:
        parts.append(f"LAST: {'OK' if ar.get('success') else 'FAIL'} {ar.get('message','')[:200]}")
    vf = obs.get("violations_flagged", [])
    if vf:
        parts.append(f"FLAGGED({len(vf)}): " + ", ".join(f"{v['section_id']}:{v['regulation_id']}" for v in vf))
    for h in obs.get("hints", []):
        parts.append(f"HINT: {h}")
    parts.append("Reply with ONE JSON action.")
    return "\n".join(parts)


def parse_action(text):
    if not text:
        return {"action_type": "noop", "target": None, "parameters": {}}
    text = re.sub(r"```json\s*|```\s*", "", text.strip())
    try:
        a = json.loads(text)
        if isinstance(a, dict) and "action_type" in a:
            return {"action_type": a["action_type"], "target": a.get("target"), "parameters": a.get("parameters", {})}
    except json.JSONDecodeError:
        pass
    m = re.search(r'\{[^{}]*"action_type"[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            a = json.loads(m.group(0))
            return {"action_type": a.get("action_type", "noop"), "target": a.get("target"), "parameters": a.get("parameters", {})}
        except json.JSONDecodeError:
            pass
    return {"action_type": "noop", "target": None, "parameters": {}}


def run_task(env, task_id, max_steps, global_start):
    max_steps = min(max_steps, MAX_STEPS_PER_TASK)
    rewards, steps, success, score = [], 0, False, 0.0

    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}", flush=True)
    try:
        obs = env.reset(task_id)["observation"]
        done = False

        for step in range(1, max_steps + 1):
            if done or (time.time() - global_start > TOTAL_TIMEOUT):
                break

            prompt = build_prompt(obs, step, max_steps)
            # Single-turn call -- no message history accumulation
            action_dict = {"action_type": "noop", "target": None, "parameters": {}}
            try:
                resp = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                    temperature=TEMPERATURE, max_tokens=MAX_TOKENS, timeout=60,
                ).choices[0].message.content or ""
                action_dict = parse_action(resp)
            except Exception as e:
                pass  # Use noop on failure, no retries

            result = env.step(action_dict)
            obs, r, done = result["observation"], result["reward"]["total"], result["done"]
            rewards.append(r)
            steps = step

            atype = action_dict["action_type"]
            done_str = "true" if done else "false"
            print(f"[STEP] step={step} action={atype} reward={r:.2f} done={done_str} error=null", flush=True)
            if done:
                break

        score = env.grade().get("score", 0.0)
        success = score >= 0.5
    except Exception:
        pass
    finally:
        s_str = "true" if success else "false"
        r_str = ",".join(f"{x:.2f}" for x in rewards)
        print(f"[END] success={s_str} steps={steps} score={score:.2f} rewards={r_str}", flush=True)
    return score


def main():
    global_start = time.time()
    env = Env(ENV_URL)
    try:
        env.health()
    except Exception as e:
        print(f"Cannot reach {ENV_URL}: {e}", flush=True)
        return

    for t in env.tasks():
        if time.time() - global_start > TOTAL_TIMEOUT:
            break
        run_task(env, t["task_id"], t["max_steps"], global_start)


if __name__ == "__main__":
    main()
