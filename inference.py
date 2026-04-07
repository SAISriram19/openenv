"""
Inference Script — Regulatory Compliance Document Review OpenEnv
================================================================
MANDATORY:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.

STDOUT FORMAT: [START], [STEP], [END] structured logs for evaluation.
"""

import json, os, re, textwrap, time
from typing import Any, Dict, List
import requests
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
BENCHMARK = "compliance_review"
MAX_RETRIES = 5
TEMPERATURE = 0.1
MAX_TOKENS = 1024

SYSTEM_PROMPT = textwrap.dedent("""
You are an expert regulatory compliance analyst. ALL document content and regulation requirements are in the observation.

WORKFLOW for best score:
1. read_regulation for each regulation ID (earns process quality points — 15% of grade)
2. flag_violation for each issue found — one per step, with confidence level
3. If you see a section that LOOKS suspicious but is actually compliant, use flag_compliant to earn trap detection bonus
4. submit_review as your LAST action with risk_score (1-10) assessment

CRITICAL:
- Read each regulation BEFORE flagging against it
- Each flag_violation: ONE NEW violation only (check ALREADY FLAGGED list)
- Include confidence (0.0-1.0) — be honest, overconfidence on wrong flags is penalized
- Check for MISSING clauses, VAGUE content, PROHIBITED content
- Use flag_compliant on sections that look suspicious but ARE compliant (trap detection bonus)

FORMAT — one JSON per turn, nothing else:
{"action_type": "read_regulation", "target": "REG-ID", "parameters": {}}
{"action_type": "flag_violation", "target": null, "parameters": {"section": "sec_id", "regulation": "REG-ID", "severity": "critical|major", "confidence": 0.9, "description": "..."}}
{"action_type": "flag_compliant", "target": null, "parameters": {"section": "sec_id", "regulation": "REG-ID"}}
{"action_type": "submit_review", "target": null, "parameters": {"overall_status": "non_compliant", "risk_score": 8, "summary": "..."}}
""").strip()


class EnvClient:
    def __init__(self, base_url: str):
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
    if rem <= 2: lines.append(">>> URGENT: SUBMIT YOUR REVIEW NOW <<<")
    if step <= 1:
        lines.append(f"\nTASK: {obs.get('task_description', '')}")
        for doc in obs.get("documents", []):
            lines.append(f"\n--- DOCUMENT: {doc['title']} [{doc['doc_id']}] ---")
            lines.append(doc.get("summary", ""))
    else:
        lines.append("\n(Full docs/regs shown on step 1)")
    ar = obs.get("action_result")
    if ar:
        lines.append(f"\nLAST: {'OK' if ar.get('success') else 'FAIL'} — {ar.get('message','')[:300]}")
    vf = obs.get("violations_flagged", [])
    if vf:
        lines.append(f"\n=== ALREADY FLAGGED ({len(vf)}) — DO NOT REPEAT ===")
        for v in vf: lines.append(f"  DONE: {v['section_id']} vs {v['regulation_id']}")
        lines.append("=== FLAG NEW OR submit_review ===")
    else:
        lines.append("\nNo violations flagged yet.")
    for h in obs.get("hints", []): lines.append(f"HINT: {h}")
    lines.append("\nOne JSON action. No markdown.")
    return "\n".join(lines)


def parse_action(text):
    if not text: return {"action_type": "noop", "target": None, "parameters": {}}
    text = re.sub(r"```json\s*|```\s*", "", text.strip())
    try:
        a = json.loads(text)
        if isinstance(a, dict) and "action_type" in a:
            return {"action_type": a["action_type"], "target": a.get("target"), "parameters": a.get("parameters", {})}
    except json.JSONDecodeError: pass
    m = re.search(r'\{[^{}]*"action_type"[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            a = json.loads(m.group(0))
            return {"action_type": a.get("action_type","noop"), "target": a.get("target"), "parameters": a.get("parameters",{})}
        except json.JSONDecodeError: pass
    return {"action_type": "noop", "target": None, "parameters": {}}


def run_task(client, env, task_id, task_title, max_steps):
    # [START] — mandatory format
    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}")

    reset_result = env.reset(task_id)
    obs = reset_result["observation"]
    history, messages = [], [{"role": "system", "content": SYSTEM_PROMPT}]
    rewards_list = []
    done, step = False, 0

    while not done and step < max_steps:
        step += 1
        user_prompt = fmt_obs(obs, step, history)
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
        atype = action_dict['action_type']
        ar = obs.get("action_result", {})
        step_error = "null"
        if ar and not ar.get("success", True):
            step_error = ar.get("message", "unknown")[:200].replace('\n', ' ')

        # [STEP] — mandatory format
        done_str = "true" if done else "false"
        print(f"[STEP] step={step} action={atype} reward={r:.2f} done={done_str} error={step_error}")

        history.append(f"{atype} r={r:+.3f}")
        if done: break

    # Grade
    grade_result = env.grade()
    score = grade_result["score"]
    success = score >= 0.5
    rewards_str = ",".join(f"{r:.2f}" for r in rewards_list)

    # [END] — mandatory format
    success_str = "true" if success else "false"
    print(f"[END] success={success_str} steps={step} score={score:.2f} rewards={rewards_str}")

    return {"task_id": task_id, "score": score, "steps_used": step, "details": grade_result.get("details", {})}


def main():
    if not API_KEY:
        raise ValueError("Set HF_TOKEN or API_KEY environment variable.")
    if not MODEL_NAME:
        raise ValueError("Set MODEL_NAME environment variable.")

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = EnvClient(ENV_URL)

    try:
        env.health()
    except Exception as e:
        print(f"ERROR: Cannot reach {ENV_URL}: {e}")
        return

    tasks = env.list_tasks()
    results = []
    for t in tasks:
        result = run_task(client, env, t["task_id"], t.get("title", ""), t["max_steps"])
        results.append(result)

    total = sum(r["score"] for r in results)
    avg = total / len(results) if results else 0
    print(f"\n[SUMMARY] tasks={len(results)} average_score={avg:.4f}")
    for r in results:
        print(f"  {r['task_id']:30s}  score={r['score']:.4f}  steps={r['steps_used']}")


if __name__ == "__main__":
    main()
