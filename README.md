---
title: Regulatory Compliance Document Review
emoji: "\U0001F4CB"
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
app_port: 7860
tags:
  - openenv
---

# Regulatory Compliance Document Review

An OpenEnv environment where AI agents act as regulatory compliance analysts, reviewing business documents against applicable regulations. Agents investigate regulations, identify violations with precise citations, avoid false positives, and submit compliance verdicts.

## Motivation

Compliance document review requires sequential decision-making under uncertainty. Analysts balance detection (finding all violations), precision (avoiding false positives), process quality (investigating before concluding), and efficiency (working within time constraints). This environment captures these tradeoffs across 4 regulation domains.

## Tasks

| Task | Difficulty | Docs | Regs | Violations | Domain | Description |
|------|-----------|------|------|------------|--------|-------------|
| `easy_privacy_review` | Easy | 1 | 5 | 6 | Data Privacy | GDPR-style privacy policy review |
| `medium_lending_review` | Medium | 2 | 4 | 6 | Fair Lending / KYC-AML | Cross-doc loan application + lending policy |
| `hard_vendor_dpa_review` | Hard | 3 | 6 | 6 | Data Privacy + Consumer Protection | Multi-doc DPA with false-positive traps |
| `medium_employment_review` | Medium | 1 | 6 | 6 | Employment Law | Startup employee handbook review |
| `hard_financial_reporting` | Hard | 2 | 5 | 5 | Financial Reporting (SOX-like) | Quarterly report + internal controls with traps |

## Action Space

| Action | Description |
|--------|-------------|
| `read_document` | Read document overview and list sections |
| `read_section` | Read full text of a specific section |
| `read_regulation` | Read a regulation's requirements and examples |
| `search_document` | Keyword search within a document |
| `cross_reference` | Side-by-side comparison of section vs regulation |
| `flag_violation` | Flag non-compliance with section, regulation, severity, confidence, description |
| `flag_compliant` | Mark a section as compliant with a regulation |
| `submit_review` | Submit final verdict with overall_status, risk_score, and summary |

## Reward Design

Dense per-step rewards for every action type. Investigation actions (read_regulation, read_section, search_document, cross_reference) each give +0.01. Correct violation flags give +0.02 to +0.08 depending on detection progress.

## Grading (0.0 to 1.0)

| Component | Weight | Description |
|-----------|--------|-------------|
| Detection | 25-35% | Recall -- ground-truth violations found |
| Accuracy | 20-25% | Precision -- correct flags / total flags |
| Process Quality | 15% | Did agent read regulations before flagging? |
| Confidence Calibration | Variable | Overconfident wrong flags penalized more |
| Trap Detection | Up to 5% | Bonus for correctly identifying compliant clauses |
| Task-specific | 0-15% | Cross-doc coverage, multi-domain coverage |
| Review Quality | 10-15% | Submitted review with correct status |
| Efficiency | 10-15% | Graduated by step ratio |

`flag_violation` accepts an optional `confidence` parameter (0.0-1.0). High confidence on incorrect flags incurs a larger penalty than low confidence. Hard tasks include compliant-looking clauses; agents can use `flag_compliant` on these to earn a small bonus. `submit_review` accepts an optional `risk_score` (1-10).

## Baseline Scores

GPT-4o (OpenAI API):

| Task | Score | Detected | FP | Steps |
|------|-------|----------|----|-------|
| easy_privacy_review | 0.77 | 5/6 | 0 | 11/20 |
| medium_lending_review | 0.93 | 5/6 | 0 | 10/20 |
| hard_vendor_dpa_review | 0.89 | 5/6 | 1 | 13/30 |
| medium_employment_review | 0.93 | 6/6 | 0 | 13/20 |
| hard_financial_reporting | 0.85 | 5/5 | 0 | 14/25 |
| Average | 0.87 | | | |

GPT-4o-mini:

| Task | Score | Detected | FP | Steps |
|------|-------|----------|----|-------|
| easy_privacy_review | 0.81 | 4/6 | 0 | 11/20 |
| medium_lending_review | 0.73 | 4/6 | 0 | 9/20 |
| hard_vendor_dpa_review | 0.89 | 5/6 | 1 | 14/30 |
| medium_employment_review | 0.81 | 6/6 | 0 | 10/20 |
| hard_financial_reporting | 0.84 | 4/5 | 1 | 12/25 |
| Average | 0.82 | | | |

## Setup

```bash
pip install -r requirements.txt
python server.py
```

Docker:

```bash
docker build -t compliance-review .
docker run -p 7860:7860 compliance-review
```

Inference:

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="your-token"
python inference.py
```

## Project Structure

```
compliance_env/
  inference.py        Baseline agent with structured [START]/[STEP]/[END] logs
  server.py           FastAPI server (health, tasks, reset, step, state, grade)
  openenv.yaml        OpenEnv spec manifest
  Dockerfile          Container definition
  requirements.txt    Dependencies
  tests.py            Unit tests
  env/
    models.py         Pydantic models (Action, Observation, Reward, State)
    scenarios.py      5 scenarios with documents, regulations, ground truth
    environment.py    Core environment logic
    graders.py        5 deterministic graders
```
