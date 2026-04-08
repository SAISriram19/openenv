"""
Task graders for the Regulatory Compliance Document Review environment.
Each grader scores agent performance strictly within (0.01, 0.99).
Updated: force redeploy

Scoring dimensions (consistent across all graders):
- Detection: Did the agent find the violations? (varies 25-35%)
- Accuracy: Precision — correct flags vs total flags (15-25%)
- Process Quality: Did the agent investigate before flagging? (15%)
- Review Quality: Submitted review with correct status (10-15%)
- Efficiency: Steps used relative to budget (10-15%)
- Task-specific bonus: Cross-doc, multi-domain, etc. (0-15%)
"""

from __future__ import annotations
from typing import Dict
from env.models import EnvironmentState


class BaseGrader:
    task_id: str = ""
    difficulty: str = ""
    def grade(self, state: EnvironmentState) -> float:
        raise NotImplementedError
    def _clamp(self, v: float) -> float:
        epsilon = 0.01
        return max(epsilon, min(round(v, 4), 1.0 - epsilon))
    def _efficiency(self, state, weight):
        if not state.review_submitted or state.detected_correctly == 0:
            return 0.0
        ratio = state.step_number / state.max_steps
        if ratio <= 0.35: return weight
        elif ratio <= 0.50: return weight * 0.75
        elif ratio <= 0.70: return weight * 0.50
        elif ratio <= 0.90: return weight * 0.25
        return 0.0
    def _process_quality(self, state, weight):
        return weight * state.process_quality


class EasyGrader(BaseGrader):
    """Easy: 1 doc, 5-6 regs. Detection 35%, Accuracy 20%, Process 15%, Review 15%, Efficiency 15%"""
    task_id = "easy_privacy_review"
    difficulty = "easy"
    def grade(self, state: EnvironmentState) -> float:
        s = 0.0
        gt, det, fps = state.ground_truth_violations, state.detected_correctly, state.false_positives
        s += 0.35 * (det / max(gt, 1))
        total_f = det + fps
        if total_f > 0: s += 0.20 * (det / total_f)
        s += self._process_quality(state, 0.15)
        if state.review_submitted:
            s += 0.05
            if state.overall_status == "non_compliant": s += 0.10
        s += self._efficiency(state, 0.15)
        return self._clamp(s)


class MediumGrader(BaseGrader):
    """Medium: 2 docs, cross-doc required. Detection 30%, Accuracy 20%, Cross-doc 15%, Process 15%, Review 10%, Efficiency 10%"""
    task_id = "medium_lending_review"
    difficulty = "medium"
    def grade(self, state: EnvironmentState) -> float:
        s = 0.0
        gt, det, fps = state.ground_truth_violations, state.detected_correctly, state.false_positives
        s += 0.30 * (det / max(gt, 1))
        total_f = det + fps
        if total_f > 0: s += 0.20 * (det / total_f)
        # Cross-doc bonus
        flagged_secs = {v.section_id for v in state.violations_flagged}
        loan = {"sec_borrower", "sec_financials", "sec_identity", "sec_decision"}
        policy = {"sec_lp_zones", "sec_lp_kyc", "sec_lp_pricing"}
        if (flagged_secs & loan) and (flagged_secs & policy): s += 0.15
        elif flagged_secs & loan or flagged_secs & policy: s += 0.06
        s += self._process_quality(state, 0.15)
        if state.review_submitted:
            s += 0.03
            if state.overall_status == "non_compliant": s += 0.07
        s += self._efficiency(state, 0.10)
        return self._clamp(s)


class HardGrader(BaseGrader):
    """Hard: 3 docs, 2 reg domains, FP traps. Detection 25%, Accuracy 25%, Multi-domain 15%, Process 15%, Review 10%, Efficiency 10%"""
    task_id = "hard_vendor_dpa_review"
    difficulty = "hard"
    def grade(self, state: EnvironmentState) -> float:
        s = 0.0
        gt, det, fps = state.ground_truth_violations, state.detected_correctly, state.false_positives
        s += 0.25 * (det / max(gt, 1))
        total_f = det + fps
        if total_f > 0: s += 0.25 * (det / total_f)
        # Multi-domain bonus
        flagged_regs = {v.regulation_id for v in state.violations_flagged}
        dp = {r for r in flagged_regs if r.startswith("REG-DP")}
        cp = {r for r in flagged_regs if r.startswith("REG-CP")}
        if dp and cp: s += 0.15
        elif dp or cp: s += 0.05
        s += self._process_quality(state, 0.15)
        if state.review_submitted:
            s += 0.03
            if state.overall_status == "non_compliant": s += 0.07
        s += self._efficiency(state, 0.10)
        return self._clamp(s)


class EmploymentGrader(BaseGrader):
    """Medium: 1 doc, 6 regs. Detection 35%, Accuracy 20%, Process 15%, Review 15%, Efficiency 15%"""
    task_id = "medium_employment_review"
    difficulty = "medium"
    def grade(self, state: EnvironmentState) -> float:
        s = 0.0
        gt, det, fps = state.ground_truth_violations, state.detected_correctly, state.false_positives
        s += 0.35 * (det / max(gt, 1))
        total_f = det + fps
        if total_f > 0: s += 0.20 * (det / total_f)
        s += self._process_quality(state, 0.15)
        if state.review_submitted:
            s += 0.05
            if state.overall_status == "non_compliant": s += 0.10
        s += self._efficiency(state, 0.15)
        return self._clamp(s)


class FinancialGrader(BaseGrader):
    """Hard: 2 docs, cross-doc, FP traps. Detection 25%, Accuracy 25%, Cross-doc 15%, Process 15%, Review 10%, Efficiency 10%"""
    task_id = "hard_financial_reporting"
    difficulty = "hard"
    def grade(self, state: EnvironmentState) -> float:
        s = 0.0
        gt, det, fps = state.ground_truth_violations, state.detected_correctly, state.false_positives
        s += 0.25 * (det / max(gt, 1))
        total_f = det + fps
        if total_f > 0: s += 0.25 * (det / total_f)
        # Cross-doc: report + controls memo
        flagged_secs = {v.section_id for v in state.violations_flagged}
        report = {"sec_revenue", "sec_expenses", "sec_cash_flow", "sec_related_party"}
        controls = {"sec_controls_revenue", "sec_controls_audit", "sec_controls_cfo"}
        if (flagged_secs & report) and (flagged_secs & controls): s += 0.15
        elif (flagged_secs & report) or (flagged_secs & controls): s += 0.05
        s += self._process_quality(state, 0.15)
        if state.review_submitted:
            s += 0.03
            if state.overall_status == "non_compliant": s += 0.07
        s += self._efficiency(state, 0.10)
        return self._clamp(s)


GRADERS = {
    "easy_privacy_review": EasyGrader(),
    "medium_lending_review": MediumGrader(),
    "hard_vendor_dpa_review": HardGrader(),
    "medium_employment_review": EmploymentGrader(),
    "hard_financial_reporting": FinancialGrader(),
}


def grade_episode(state: EnvironmentState) -> float:
    grader = GRADERS.get(state.task_id)
    if grader is None:
        raise ValueError(f"No grader for task '{state.task_id}'")
    score = grader.grade(state)
    # Double safety: ensure strictly between 0 and 1
    return max(0.01, min(score, 0.99))
