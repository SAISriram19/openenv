"""
Core OpenEnv environment for Regulatory Compliance Document Review.
Implements the full OpenEnv spec: step() / reset() / state()
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from env.models import (
    Action, ActionResult, ActionType, ComplianceStatus, DocumentInfo,
    DocumentSection, EnvironmentState, Observation, RegulationRule,
    Reward, Severity, ViolationFlag,
)
from env.scenarios import SCENARIOS, Scenario


class ComplianceReviewEnv:
    """Regulatory Compliance Document Review Environment."""

    def __init__(self, task_id: str = "easy_privacy_review"):
        self._task_id = task_id
        self._scenario: Optional[Scenario] = None
        self._step_number: int = 0
        self._done: bool = False
        self._actions_taken: List[Dict[str, Any]] = []
        self._violations_flagged: List[ViolationFlag] = []
        self._compliant_flags: List[str] = []
        self._notes: List[str] = []
        self._cumulative_reward: float = 0.0
        self._review_submitted: bool = False
        self._overall_status: Optional[str] = None
        self._review_summary: Optional[str] = None
        # Process quality tracking — which regs/sections were investigated before flagging
        self._regs_read: set = set()           # regulation IDs the agent has read
        self._sections_read: set = set()       # "doc_id:section_id" pairs agent has read
        self._cross_refs_done: set = set()     # "section_id:reg_id" pairs cross-referenced
        self._flags_with_due_diligence: int = 0  # flags where agent read reg AND section first
        self._correct_compliant_flags: int = 0   # correctly identified traps as compliant
        self._confidence_scores: List[float] = [] # confidence on each flag_violation
        self._risk_score: Optional[int] = None    # overall risk assessment (1-10)

    # ------------------------------------------------------------------
    # OpenEnv API
    # ------------------------------------------------------------------

    def reset(self, task_id: Optional[str] = None) -> Observation:
        if task_id:
            self._task_id = task_id
        if self._task_id not in SCENARIOS:
            raise ValueError(f"Unknown task_id '{self._task_id}'. Available: {list(SCENARIOS.keys())}")

        self._scenario = SCENARIOS[self._task_id]
        self._step_number = 0
        self._done = False
        self._actions_taken = []
        self._violations_flagged = []
        self._compliant_flags = []
        self._notes = []
        self._cumulative_reward = 0.0
        self._review_submitted = False
        self._overall_status = None
        self._review_summary = None
        self._regs_read = set()
        self._sections_read = set()
        self._cross_refs_done = set()
        self._flags_with_due_diligence = 0
        self._correct_compliant_flags = 0
        self._confidence_scores = []
        self._risk_score = None

        obs = self._build_observation(
            ActionResult(success=True, message="Compliance review environment initialized. Begin your review.")
        )
        return obs

    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        """Process one action per step. Supports 'batch' action_type for multi-command (max 3).
        
        Multi-command: send action_type='batch' with parameters={'commands': [
            {"action_type": "read_regulation", "target": "REG-DP-001"},
            {"action_type": "flag_violation", "parameters": {"section": "...", ...}}
        ]}
        Single command: send normally as before.
        """
        if self._done:
            obs = self._build_observation(ActionResult(success=False, message="Review already submitted."))
            return obs, Reward(total=0.0), True, {"message": "Episode done"}
        if self._scenario is None:
            raise RuntimeError("Call reset() first.")

        self._step_number += 1

        # Handle batch commands (max 3 per step)
        if action.action_type == ActionType.NOOP and action.parameters.get("commands"):
            commands = action.parameters["commands"][:3]  # max 3
            results = []
            for cmd in commands:
                sub_action = Action(
                    action_type=cmd.get("action_type", "noop"),
                    target=cmd.get("target"),
                    parameters=cmd.get("parameters", {}),
                )
                self._actions_taken.append(sub_action.model_dump())
                result = self._execute_action(sub_action)
                results.append(result)
                if sub_action.action_type == ActionType.SUBMIT_REVIEW:
                    self._done = True
                    break
            action_result = ActionResult(
                success=all(r.success for r in results),
                message="\n---\n".join(r.message for r in results),
                data={"batch_results": [r.model_dump() for r in results]},
            )
        else:
            self._actions_taken.append(action.model_dump())
            action_result = self._execute_action(action)

        reward = self._compute_reward(action)
        self._cumulative_reward += reward.total

        if self._step_number >= self._scenario.max_steps:
            self._done = True
            # Auto-submit if agent ran out of steps without submitting
            if not self._review_submitted:
                self._review_submitted = True
                self._overall_status = "non_compliant" if len(self._violations_flagged) > 0 else "needs_review"
                self._review_summary = "Auto-submitted: agent ran out of steps."
        if action.action_type == ActionType.SUBMIT_REVIEW:
            self._done = True

        obs = self._build_observation(action_result)
        info = {
            "step": self._step_number,
            "cumulative_reward": self._cumulative_reward,
            "violations_flagged": len(self._violations_flagged),
        }
        return obs, reward, self._done, info

    def state(self) -> EnvironmentState:
        if self._scenario is None:
            raise RuntimeError("Call reset() first.")
        gt = self._scenario.ground_truth_violations
        detected = self._count_correct_detections()
        fps = self._count_false_positives()
        return EnvironmentState(
            task_id=self._task_id,
            step_number=self._step_number,
            max_steps=self._scenario.max_steps,
            done=self._done,
            observation=self._build_observation(None),
            cumulative_reward=self._cumulative_reward,
            actions_taken=self._actions_taken,
            violations_flagged=self._violations_flagged,
            compliant_flags=self._compliant_flags,
            notes=self._notes,
            review_submitted=self._review_submitted,
            overall_status=self._overall_status,
            review_summary=self._review_summary,
            ground_truth_violations=len(gt),
            detected_correctly=detected,
            false_positives=fps,
            missed_violations=len(gt) - detected,
            process_quality=self._flags_with_due_diligence / max(len(self._violations_flagged), 1) if self._violations_flagged else 0.0,
            regs_read=len(self._regs_read),
            sections_read=len(self._sections_read),
            correct_compliant_flags=self._correct_compliant_flags,
            confidence_calibration=self._compute_confidence_calibration(),
            risk_score=self._risk_score,
        )

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def _execute_action(self, action: Action) -> ActionResult:
        handler = {
            ActionType.READ_DOCUMENT: self._handle_read_document,
            ActionType.READ_SECTION: self._handle_read_section,
            ActionType.READ_REGULATION: self._handle_read_regulation,
            ActionType.SEARCH_DOCUMENT: self._handle_search_document,
            ActionType.CROSS_REFERENCE: self._handle_cross_reference,
            ActionType.FLAG_VIOLATION: self._handle_flag_violation,
            ActionType.FLAG_COMPLIANT: self._handle_flag_compliant,
            ActionType.REQUEST_CLARIFICATION: self._handle_request_clarification,
            ActionType.ADD_NOTE: self._handle_add_note,
            ActionType.SUBMIT_REVIEW: self._handle_submit_review,
            ActionType.NOOP: self._handle_noop,
        }.get(action.action_type)
        if handler is None:
            return ActionResult(success=False, message=f"Unknown action: {action.action_type}")
        return handler(action)

    def _handle_read_document(self, action: Action) -> ActionResult:
        doc_id = action.target
        if not doc_id or doc_id not in self._scenario.documents:
            return ActionResult(success=False,
                message=f"Unknown document '{doc_id}'. Available: {list(self._scenario.documents.keys())}")
        doc = self._scenario.documents[doc_id]
        sections = doc.get("sections", {})
        overview = [f"  - {sid}: {s['title']} (page {s.get('page', '?')})" for sid, s in sections.items()]
        return ActionResult(
            success=True,
            message=f"Document: {doc['title']}\nType: {doc['type']}\nParties: {doc.get('parties', [])}\n"
                    f"Date: {doc.get('date', 'N/A')}\nSummary: {doc.get('summary', '')}\n\nSections:\n" + "\n".join(overview),
            data={"doc_id": doc_id, "title": doc["title"], "section_ids": list(sections.keys())},
        )

    def _handle_read_section(self, action: Action) -> ActionResult:
        doc_id = action.target
        section_id = action.parameters.get("section")
        if not doc_id or doc_id not in self._scenario.documents:
            return ActionResult(success=False, message=f"Unknown document '{doc_id}'.")
        sections = self._scenario.documents[doc_id].get("sections", {})
        if not section_id or section_id not in sections:
            return ActionResult(success=False,
                message=f"Unknown section '{section_id}'. Available: {list(sections.keys())}")
        sec = sections[section_id]
        self._sections_read.add(f"{doc_id}:{section_id}")
        return ActionResult(
            success=True,
            message=f"=== {sec['title']} (Page {sec.get('page', '?')}) ===\n\n{sec['content']}",
            data={"doc_id": doc_id, "section_id": section_id, "title": sec["title"], "content": sec["content"]},
        )

    def _handle_read_regulation(self, action: Action) -> ActionResult:
        reg_id = action.target
        if not reg_id or reg_id not in self._scenario.regulations:
            return ActionResult(success=False,
                message=f"Unknown regulation '{reg_id}'. Available: {list(self._scenario.regulations.keys())}")
        reg = self._scenario.regulations[reg_id]
        self._regs_read.add(reg_id)
        text = (
            f"=== {reg['title']} [{reg_id}] ===\n"
            f"Domain: {reg['domain']}\nSeverity if violated: {reg['severity']}\n\n"
            f"Description: {reg['description']}\n\n"
            f"Requirement:\n{reg['requirement']}"
        )
        if reg.get("examples_of_compliance"):
            text += f"\n\nExample of compliance: {reg['examples_of_compliance']}"
        if reg.get("examples_of_violation"):
            text += f"\n\nExample of violation: {reg['examples_of_violation']}"
        return ActionResult(success=True, message=text, data={"reg_id": reg_id})

    def _handle_search_document(self, action: Action) -> ActionResult:
        doc_id = action.target
        query = action.parameters.get("query", "").lower()
        if not doc_id or doc_id not in self._scenario.documents:
            return ActionResult(success=False, message=f"Unknown document '{doc_id}'.")
        if not query:
            return ActionResult(success=False, message="Provide 'query' parameter to search.")
        sections = self._scenario.documents[doc_id].get("sections", {})
        matches = []
        for sid, sec in sections.items():
            if query in sec["content"].lower() or query in sec["title"].lower():
                snippet = sec["content"][:200] + ("..." if len(sec["content"]) > 200 else "")
                matches.append({"section_id": sid, "title": sec["title"], "snippet": snippet})
        if not matches:
            return ActionResult(success=True, message=f"No matches for '{query}' in {doc_id}.", data=[])
        result_text = f"Search '{query}' in {doc_id} — {len(matches)} match(es):\n"
        for m in matches:
            result_text += f"\n  [{m['section_id']}] {m['title']}: {m['snippet']}"
        return ActionResult(success=True, message=result_text, data=matches)

    def _handle_cross_reference(self, action: Action) -> ActionResult:
        doc_id = action.target
        section_id = action.parameters.get("section")
        reg_id = action.parameters.get("regulation")
        if not all([doc_id, section_id, reg_id]):
            return ActionResult(success=False, message="Provide target (doc_id), section, and regulation parameters.")
        if doc_id not in self._scenario.documents:
            return ActionResult(success=False, message=f"Unknown document '{doc_id}'.")
        sections = self._scenario.documents[doc_id].get("sections", {})
        if section_id not in sections:
            return ActionResult(success=False, message=f"Unknown section '{section_id}'.")
        if reg_id not in self._scenario.regulations:
            return ActionResult(success=False, message=f"Unknown regulation '{reg_id}'.")
        sec = sections[section_id]
        reg = self._scenario.regulations[reg_id]
        self._cross_refs_done.add(f"{section_id}:{reg_id}")
        return ActionResult(
            success=True,
            message=f"Cross-reference: [{section_id}] {sec['title']} vs [{reg_id}] {reg['title']}\n\n"
                    f"Document text:\n{sec['content']}\n\nRegulation requirement:\n{reg['requirement']}",
            data={"section_id": section_id, "regulation_id": reg_id},
        )

    def _handle_flag_violation(self, action: Action) -> ActionResult:
        section_id = action.parameters.get("section", "")
        regulation_id = action.parameters.get("regulation", "")
        severity_str = action.parameters.get("severity", "major")
        description = action.parameters.get("description", "")
        suggested_fix = action.parameters.get("suggested_fix", "")
        if not section_id or not regulation_id or not description:
            return ActionResult(success=False,
                message="Flag violation requires: section, regulation, and description parameters.")
        # Reject duplicates — same section+regulation already flagged
        for existing in self._violations_flagged:
            if existing.section_id == section_id and existing.regulation_id == regulation_id:
                return ActionResult(success=False,
                    message=f"Already flagged: {section_id} vs {regulation_id}. Flag a different violation or submit_review.")
        try:
            sev = Severity(severity_str)
        except ValueError:
            sev = Severity.MAJOR
        flag = ViolationFlag(
            section_id=section_id, regulation_id=regulation_id,
            severity=sev, description=description, suggested_fix=suggested_fix,
        )
        self._violations_flagged.append(flag)
        # Track confidence calibration
        confidence = action.parameters.get("confidence", 0.8)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (ValueError, TypeError):
            confidence = 0.8
        self._confidence_scores.append(confidence)
        # Track due diligence: did agent read the regulation before flagging?
        if regulation_id in self._regs_read:
            self._flags_with_due_diligence += 1
        return ActionResult(
            success=True,
            message=f"Violation flagged: [{sev.value.upper()}] {section_id} vs {regulation_id} (confidence: {confidence:.0%})\n{description}",
            data=flag.model_dump(),
        )

    def _handle_flag_compliant(self, action: Action) -> ActionResult:
        section_id = action.parameters.get("section", "")
        regulation_id = action.parameters.get("regulation", "")
        if not section_id or not regulation_id:
            return ActionResult(success=False, message="Provide section and regulation parameters.")
        key = f"{section_id}:{regulation_id}"
        self._compliant_flags.append(key)
        # Check if this is a correct trap detection (section+reg is NOT in ground truth)
        is_trap = True
        for gt in self._scenario.ground_truth_violations:
            if gt.section_id == section_id and gt.regulation_id == regulation_id:
                is_trap = False
                break
        if is_trap:
            self._correct_compliant_flags += 1
        return ActionResult(success=True,
            message=f"Marked compliant: {section_id} satisfies {regulation_id}" +
                    (" (Good catch — this section is indeed compliant)" if is_trap else ""))

    def _handle_request_clarification(self, action: Action) -> ActionResult:
        question = action.parameters.get("question", "")
        if not question:
            return ActionResult(success=False, message="Provide 'question' parameter.")
        return ActionResult(success=True,
            message="Clarification noted. In a production setting this would go to the document owner. "
                    "For this review, rely on the document text as-is and flag ambiguities as observations.")

    def _handle_add_note(self, action: Action) -> ActionResult:
        note = action.parameters.get("note", "")
        if not note:
            return ActionResult(success=False, message="Provide 'note' parameter.")
        self._notes.append(note)
        return ActionResult(success=True, message=f"Note added: {note}")

    def _handle_submit_review(self, action: Action) -> ActionResult:
        overall = action.parameters.get("overall_status", "needs_review")
        summary = action.parameters.get("summary", "")
        risk_score = action.parameters.get("risk_score", None)
        self._review_submitted = True
        self._overall_status = overall
        self._review_summary = summary
        # Risk score: agent's assessment of overall risk (1-10)
        if risk_score is not None:
            try:
                self._risk_score = max(1, min(10, int(risk_score)))
            except (ValueError, TypeError):
                self._risk_score = None
        detected = self._count_correct_detections()
        gt_count = len(self._scenario.ground_truth_violations)
        fps = self._count_false_positives()
        return ActionResult(
            success=True,
            message=f"Review submitted.\nStatus: {overall}\nViolations flagged: {len(self._violations_flagged)}\n"
                    f"Correctly detected: {detected}/{gt_count}\nFalse positives: {fps}",
            data={"overall_status": overall, "violations": len(self._violations_flagged),
                  "correct": detected, "missed": gt_count - detected, "false_positives": fps},
        )

    def _handle_noop(self, action: Action) -> ActionResult:
        return ActionResult(success=True, message="No action taken.")

    # ------------------------------------------------------------------
    # Grading helpers
    # ------------------------------------------------------------------

    def _count_correct_detections(self) -> int:
        count = 0
        for gt in self._scenario.ground_truth_violations:
            for flag in self._violations_flagged:
                if self._matches_violation(flag, gt):
                    count += 1
                    break
        return count

    def _count_false_positives(self) -> int:
        fps = 0
        for flag in self._violations_flagged:
            matched = False
            for gt in self._scenario.ground_truth_violations:
                if self._matches_violation(flag, gt):
                    matched = True
                    break
            if not matched:
                fps += 1
        return fps

    def _matches_violation(self, flag: ViolationFlag, gt) -> bool:
        """Check if a flagged violation matches a ground-truth violation.

        Requires:
        1. Section ID: exact match or substring containment
        2. Regulation ID: exact match
        3. Description must mention at least 1 ground-truth keyword (prevents garbage flags)
        """
        # Section matching
        if flag.section_id != gt.section_id:
            if gt.section_id not in flag.section_id and flag.section_id not in gt.section_id:
                return False
        # Regulation must match
        if flag.regulation_id != gt.regulation_id:
            return False
        # At least 1 keyword must appear in description or suggested_fix
        search_text = (flag.description + " " + flag.suggested_fix).lower()
        matched_kw = sum(1 for kw in gt.keywords if kw.lower() in search_text)
        return matched_kw >= 1

    # ------------------------------------------------------------------
    # Observation builder
    # ------------------------------------------------------------------

    def _build_observation(self, action_result: Optional[ActionResult] = None) -> Observation:
        docs = []
        for doc_id, doc in self._scenario.documents.items():
            # Full content only on step 0 (reset). After that, just metadata.
            if self._step_number == 0:
                full_text_parts = []
                for sid, sec in doc.get("sections", {}).items():
                    full_text_parts.append(f"[{sid}] {sec['title']}:\n{sec['content']}")
                summary = "\n\n".join(full_text_parts)
            else:
                summary = f"(Full content provided on reset. Sections: {', '.join(doc.get('sections', {}).keys())})"
            docs.append(DocumentInfo(
                doc_id=doc_id, doc_type=doc["type"], title=doc["title"],
                parties=doc.get("parties", []), date=doc.get("date", ""),
                section_ids=list(doc.get("sections", {}).keys()),
                summary=summary,
            ))

        reg_ids = list(self._scenario.regulations.keys())

        # Regulation text only on reset
        if self._step_number == 0:
            reg_texts = []
            for rid, reg in self._scenario.regulations.items():
                reg_texts.append(f"[{rid}] {reg['title']} (severity: {reg['severity']}): {reg['requirement']}")
            full_task = self._scenario.task_prompt + "\n\n=== APPLICABLE REGULATIONS ===\n" + "\n\n".join(reg_texts)
        else:
            full_task = self._scenario.task_prompt

        # Urgency hints + NEXT STEP guidance
        remaining = self._scenario.max_steps - self._step_number
        dynamic_hints = []
        if self._step_number == 0:
            dynamic_hints = self._scenario.hints + [
                "ALL document content and regulation requirements are above.",
                f"Budget: {self._scenario.max_steps} steps total.",
                ">>> NEXT STEP: read_regulation for each regulation, then flag_violation for each issue found, then submit_review.",
            ]
        elif remaining <= 2 and not self._review_submitted:
            dynamic_hints = [">>> NEXT STEP: submit_review NOW — you're almost out of steps."]
        elif remaining <= 4 and not self._review_submitted:
            dynamic_hints = [">>> NEXT STEP: Flag remaining violations, then submit_review soon."]
        else:
            # Smart guidance based on current state
            regs_not_read = [r for r in reg_ids if r not in self._regs_read]
            num_flagged = len(self._violations_flagged)
            if regs_not_read and num_flagged == 0:
                dynamic_hints = [f">>> NEXT STEP: read_regulation {regs_not_read[0]} (then flag violations against it)"]
            elif num_flagged > 0 and not self._review_submitted:
                dynamic_hints = [f">>> NEXT STEP: Flag more violations or submit_review if done. ({num_flagged} flagged so far)"]

        return Observation(
            task_description=full_task,
            documents=docs,
            applicable_regulations=reg_ids,
            action_result=action_result,
            violations_flagged=copy.deepcopy(self._violations_flagged),
            compliant_flags=list(self._compliant_flags),
            notes=list(self._notes),
            step_number=self._step_number,
            max_steps=self._scenario.max_steps,
            review_submitted=self._review_submitted,
            regulations_investigated=len(self._regs_read),
            sections_investigated=len(self._sections_read),
            process_quality_score=round(self._flags_with_due_diligence / max(len(self._violations_flagged), 1), 2) if self._violations_flagged else 0.0,
            hints=dynamic_hints,
        )

    # ------------------------------------------------------------------
    # Reward computation
    # ------------------------------------------------------------------

    def _compute_reward(self, action: Action) -> Reward:
        gt_count = len(self._scenario.ground_truth_violations)
        detected = self._count_correct_detections()
        fps = self._count_false_positives()

        # detection_score: fraction of violations found (recall)
        detection_score = detected / max(gt_count, 1)
        # accuracy_score: precision — correct / total flagged
        accuracy_score = detected / max(detected + fps, 1)
        # completeness_score: severity-weighted coverage
        completeness_score = self._severity_weighted_coverage()
        # process_quality: did agent investigate before flagging?
        total_flags = len(self._violations_flagged)
        process_quality = self._flags_with_due_diligence / max(total_flags, 1) if total_flags > 0 else 0.0

        fp_penalty = -min(0.4, fps * 0.08)

        # Dense action reward — small bonus for investigation steps
        action_bonus = 0.0
        if action.action_type in (ActionType.READ_SECTION, ActionType.READ_REGULATION,
                                   ActionType.CROSS_REFERENCE, ActionType.SEARCH_DOCUMENT):
            action_bonus = 0.01
        elif action.action_type == ActionType.READ_DOCUMENT:
            action_bonus = 0.005

        efficiency_bonus = 0.0
        if self._done and detection_score > 0.5:
            ratio = self._step_number / self._scenario.max_steps
            if ratio < 0.5:
                efficiency_bonus = 0.08
            elif ratio < 0.75:
                efficiency_bonus = 0.04

        # Confidence calibration — gentle nudge, not score killer
        confidence_penalty = 0.0
        if self._confidence_scores and fps > 0:
            for i, flag in enumerate(self._violations_flagged):
                matched = any(self._matches_violation(flag, gt) for gt in self._scenario.ground_truth_violations)
                if not matched and i < len(self._confidence_scores):
                    conf = self._confidence_scores[i]
                    confidence_penalty -= conf * 0.02  # reduced from 0.05 to 0.02

        # Trap detection bonus — correctly marking compliant sections
        trap_bonus = min(0.05, self._correct_compliant_flags * 0.02)

        total = (0.25 * detection_score + 0.20 * accuracy_score + 0.25 * completeness_score
                 + 0.15 * process_quality + efficiency_bonus + fp_penalty + action_bonus
                 + confidence_penalty + trap_bonus)
        total = max(-1.0, min(1.0, total))

        return Reward(
            total=round(total, 4),
            detection_score=round(detection_score, 4),
            accuracy_score=round(accuracy_score, 4),
            completeness_score=round(completeness_score, 4),
            false_positive_penalty=round(fp_penalty, 4),
            efficiency_bonus=round(efficiency_bonus + action_bonus, 4),
            breakdown={
                "ground_truth_count": gt_count, "detected": detected,
                "false_positives": fps, "missed": gt_count - detected,
                "steps_used": self._step_number, "max_steps": self._scenario.max_steps,
                "process_quality": round(process_quality, 4),
                "regs_read": len(self._regs_read),
                "sections_read": len(self._sections_read),
                "flags_with_due_diligence": self._flags_with_due_diligence,
                "confidence_penalty": round(confidence_penalty, 4),
                "trap_bonus": round(trap_bonus, 4),
                "correct_compliant_flags": self._correct_compliant_flags,
            },
        )

    def _compute_confidence_calibration(self) -> float:
        """Measure how well-calibrated the agent's confidence scores are.
        Returns 0-1 where 1 = perfectly calibrated (high confidence on correct, low on wrong)."""
        if not self._confidence_scores or not self._violations_flagged:
            return 0.0
        correct_confs = []
        wrong_confs = []
        for i, flag in enumerate(self._violations_flagged):
            matched = any(self._matches_violation(flag, gt) for gt in self._scenario.ground_truth_violations)
            if i < len(self._confidence_scores):
                if matched:
                    correct_confs.append(self._confidence_scores[i])
                else:
                    wrong_confs.append(self._confidence_scores[i])
        # Good calibration: high confidence on correct, low on wrong
        avg_correct = sum(correct_confs) / len(correct_confs) if correct_confs else 0.0
        avg_wrong = sum(wrong_confs) / len(wrong_confs) if wrong_confs else 0.0
        if not wrong_confs:
            return avg_correct  # no wrong flags = calibration based on correct confidence
        return max(0.0, avg_correct - avg_wrong)  # separation between correct and wrong confidence

    def _severity_weighted_coverage(self) -> float:
        """Completeness weighted by severity — critical=3, major=2, minor/observation=1."""
        weights = {"critical": 3.0, "major": 2.0, "minor": 1.0, "observation": 1.0}
        total_weight = 0.0
        detected_weight = 0.0
        for gt in self._scenario.ground_truth_violations:
            w = weights.get(gt.severity, 1.0)
            total_weight += w
            for flag in self._violations_flagged:
                if self._matches_violation(flag, gt):
                    detected_weight += w
                    break
        return detected_weight / max(total_weight, 1.0)
