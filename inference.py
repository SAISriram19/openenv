"""
Inference Script -- Regulatory Compliance Document Review OpenEnv
"""

import json, os, re, textwrap, time
from typing import Any, Dict, List
import requests
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
BENCHMARK = "compliance_review"
MAX_RETRIES = 5
TEMPERATURE = 0.1
MAX_TOKENS = 1024

SYSTEM_PROMPT = textwrap.dedent("""
You are an expert regulatory compliance analyst. ALL document content and regulation requirements are in the observation.

WORKFLOW for best score:
1. read_regulation for each regulation ID (earns process quality points)
2. flag_violation for each issue found, one per step, with confidence level
3. If you see a section that LOOKS suspicious but is actually compliant, use flag_compliant
4. submit_review as your LAST action with risk_score (1-10) assessment

CRITICAL:
- Read each regulation BEFORE flagging against it
- Each flag_violation: ONE NEW violation only (check ALREADY FLAGGED list)
- Include confidence (0.0-1.0), be honest
- Check for MISSING clauses, VAGUE content, PROHIBITED content
- Use flag_compliant on sections that look suspicious but ARE compliant

FORMAT, one JSON per turn, nothing else:
{"action_type": "read_regulation", "target": "REG-ID", "parameters": {}}
{"action_type": "flag_violation", "target": null, "parameters": {"section": "sec_id", "regulation": "REG-ID", "severity": "critical|major", "confidence": 0.9, "description": "..."}}
{"action_type": "flag_compliant", "target": null, "parameters": {"section": "sec_id", "regulation": "REG-ID"}}
{"action_type": "submit_review", "target": null, "parameters": {"overall_status": "non_compliant", "risk_score": 8, "summary": "..."}}
""").strip()


class EnvClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.s = requests.Session()
    def health(self): return self.s.get(f"{self.base_url}/health", timeout=10).json()
    def reset(self, task_id): return self.s.post(f"{self.base_url}/reset", json={"task_id": task_id}, timeout=10).json()
    def step(self, action): return self.s.post(f"{self.base_url}/step", json=action, timeout=10).json()
    def state(self): return self.s.get(f"{self.base_url}/state", timeout=10).json()
    def grade(self): return self.s.post(f"{self.base_url}/grade", timeout=10).json()
    def list_tasks(self): return self.s.get(f"{self.base_url}/tasks", timeout=10).json()["tasks"]


def fmt_obs(obs, step, history):
    mx = obs.get('max_steps', 20)
    rem = mx - step
    lines = [f"=== STEP {step}/{mx} ({rem} left) ==="]
    if rem <= 2:
        lines.append(">>> URGENT: SUBMIT YOUR REVIEW NOW <<<")
    if step <= 1:
        lines.append(f"\nTASK: {obs.get('task_description', '')}")
        for doc in obs.get("documents", []):
            lines.append(f"\n--- DOCUMENT: {doc['title']} [{doc['doc_id']}] ---")
            lines.append(doc.get("summary", ""))
    else:
        lines.append("\n(Full docs/regs shown on step 1)")
    ar = obs.get("action_result")
    if ar:
        lines.append(f"\nLAST: {'OK' if ar.get('success') else 'FAIL'} -- {ar.get('message','')[:300]}")
    vf = obs.get("violations_flagged", [])
    if vf:
        lines.append(f"\n=== ALREADY FLAGGED ({len(vf)}) -- DO NOT REPEAT ===")
        for v in vf:
            lines.append(f"  DONE: {v['section_id']} vs {v['regulation_id']}")
        lines.append("=== FLAG NEW OR submit_review ===")
    else:
        lines.append("\nNo violations flagged yet.")
    for h in obs.get("hints", []):
        lines.append(f"HINT: {h}")
    lines.append("\nOne JSON action. No markdown.")
    return "\n".join(lines)


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


def run_task(env, task_id, max_steps):
    rewards_list = []
    steps_taken = 0
    success = False
    score = 0.0

    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}")

    try:
        reset_result = env.reset(task_id)
        obs = reset_result["observation"]
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        done = False

        for step in range(1, max_steps + 1):
            if done:
                break

            user_prompt = fmt_obs(obs, step, [])
            messages.append({"role": "user", "content": user_prompt})

            action_dict = None
            error_msg = "null"
            for attempt in range(MAX_RETRIES):
                try:
                    comp = client.chat.completions.create(
                        model=MODEL_NAME, messages=messages,
                        temperature=TEMPERATURE, max_tokens=MAX_TOKENS, stream=False)
                    resp = comp.choices[0].message.content or ""
                    action_dict = parse_action(resp)
                    messages.append({"role": "assistant", "content": resp})
                    break
                except Exception as e:
                    error_msg = str(e).replace('\n', ' ')[:200]
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(min(5 * (attempt + 1), 15))
                    else:
                        action_dict = {"action_type": "noop", "target": None, "parameters": {}}

            step_result = env.step(action_dict)
            obs = step_result["observation"]
            reward = step_result["reward"]
            done = step_result["done"]
            r = reward["total"]
            rewards_list.append(r)
            steps_taken = step

            atype = action_dict["action_type"]
            ar = obs.get("action_result", {})
            step_error = "null"
            if ar and not ar.get("success", True):
                step_error = ar.get("message", "unknown")[:200].replace('\n', ' ')

            done_str = "true" if done else "false"
            print(f"[STEP] step={step} action={atype} reward={r:.2f} done={done_str} error={step_error}")

            if done:
                break

        grade_result = env.grade()
        score = grade_result["score"]
        success = score >= 0.5

    except Exception as e:
        pass
    finally:
        success_str = "true" if success else "false"
        rewards_str = ",".join(f"{r:.2f}" for r in rewards_list)
        print(f"[END] success={success_str} steps={steps_taken} rewards={rewards_str}")

    return {"task_id": task_id, "score": score, "steps_used": steps_taken}


def main():
    env = EnvClient(ENV_URL)

    try:
        env.health()
    except Exception as e:
        print(f"ERROR: Cannot reach {ENV_URL}: {e}")
        return

    tasks = env.list_tasks()
    results = []
    for t in tasks:
        result = run_task(env, t["task_id"], t["max_steps"])
        results.append(result)


if __name__ == "__main__":
    main()
