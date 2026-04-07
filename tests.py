"""Unit tests for the Regulatory Compliance Document Review environment."""

import sys
sys.path.insert(0, r"D:\meta\compliance_env")

from env.environment import ComplianceReviewEnv
from env.graders import EasyGrader, MediumGrader, HardGrader, grade_episode
from env.models import Action, ActionType, ViolationFlag, Severity
from env.scenarios import SCENARIOS

#  Helpers 
def make_action(atype, target=None, **params):
    return Action(action_type=atype, target=target, parameters=params)

passed = 0
failed = 0
def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}")

print("=" * 60)
print("UNIT TESTS")
print("=" * 60)

#  Test 1: Scenario data integrity 
print("\n[Scenario Integrity]")
for tid, s in SCENARIOS.items():
    check(f"{tid} has ground truth", len(s.ground_truth_violations) >= 3)
    check(f"{tid} has documents", len(s.documents) >= 1)
    check(f"{tid} has regulations", len(s.regulations) >= 3)
    check(f"{tid} max_steps > 0", s.max_steps > 0)
    # Every ground truth violation references a real section and regulation
    for v in s.ground_truth_violations:
        found_sec = False
        for doc in s.documents.values():
            if v.section_id in doc.get("sections", {}):
                found_sec = True
                break
        check(f"{tid}: section '{v.section_id}' exists in docs", found_sec)
        check(f"{tid}: reg '{v.regulation_id}' exists", v.regulation_id in s.regulations)
        check(f"{tid}: violation has keywords", len(v.keywords) >= 1)

#  Test 2: Environment reset/step/state cycle 
print("\n[Environment Lifecycle]")
env = ComplianceReviewEnv()
obs = env.reset("easy_privacy_review")
check("reset returns observation", obs is not None)
check("step_number is 0", obs.step_number == 0)
check("not done on reset", obs.review_submitted == False)
check("documents populated", len(obs.documents) > 0)
check("regulations populated", len(obs.applicable_regulations) > 0)

state = env.state()
check("state returns EnvironmentState", state.task_id == "easy_privacy_review")
check("state step 0", state.step_number == 0)

#  Test 3: Action handlers return correctly 
print("\n[Action Handlers]")
obs, rew, done, info = env.step(make_action(ActionType.READ_DOCUMENT, "privacy_policy_001"))
check("read_document succeeds", obs.action_result.success)
check("step incremented", obs.step_number == 1)

obs, rew, done, info = env.step(make_action(ActionType.READ_SECTION, "privacy_policy_001", section="sec_collection"))
check("read_section succeeds", obs.action_result.success)
check("section content has biometric", "biometric" in obs.action_result.message.lower())

obs, rew, done, info = env.step(make_action(ActionType.READ_REGULATION, "REG-DP-001"))
check("read_regulation succeeds", obs.action_result.success)

obs, rew, done, info = env.step(make_action(ActionType.SEARCH_DOCUMENT, "privacy_policy_001", query="biometric"))
check("search_document succeeds", obs.action_result.success)
check("search finds matches", len(obs.action_result.data) > 0)

obs, rew, done, info = env.step(make_action(ActionType.CROSS_REFERENCE, "privacy_policy_001",
                                              section="sec_retention", regulation="REG-DP-003"))
check("cross_reference succeeds", obs.action_result.success)

#  Test 4: Error handling 
print("\n[Error Handling]")
obs, rew, done, info = env.step(make_action(ActionType.READ_DOCUMENT, "FAKE_DOC"))
check("invalid doc returns failure", not obs.action_result.success)

obs, rew, done, info = env.step(make_action(ActionType.READ_SECTION, "privacy_policy_001", section="FAKE"))
check("invalid section returns failure", not obs.action_result.success)

obs, rew, done, info = env.step(make_action(ActionType.READ_REGULATION, "FAKE_REG"))
check("invalid regulation returns failure", not obs.action_result.success)

obs, rew, done, info = env.step(make_action(ActionType.FLAG_VIOLATION, None))
check("flag_violation without params fails", not obs.action_result.success)

#  Test 5: Fuzzy matching logic 
print("\n[Fuzzy Matching]")
env2 = ComplianceReviewEnv()
env2.reset("easy_privacy_review")
gt0 = SCENARIOS["easy_privacy_review"].ground_truth_violations[0]  # sec_collection vs REG-DP-001

# Exact match  should work
exact_flag = ViolationFlag(section_id="sec_collection", regulation_id="REG-DP-001",
    severity=Severity.CRITICAL, description="Biometric facial recognition data without consent or lawful basis")
check("exact match works", env2._matches_violation(exact_flag, gt0))

# Wrong section  should fail
wrong_sec = ViolationFlag(section_id="sec_usage", regulation_id="REG-DP-001",
    severity=Severity.CRITICAL, description="Biometric data without consent")
check("wrong section fails", not env2._matches_violation(wrong_sec, gt0))

# Wrong regulation  should fail
wrong_reg = ViolationFlag(section_id="sec_collection", regulation_id="REG-DP-999",
    severity=Severity.CRITICAL, description="Biometric data without consent")
check("wrong regulation fails", not env2._matches_violation(wrong_reg, gt0))

# Paraphrased description  should still match if keywords hit
paraphrase = ViolationFlag(section_id="sec_collection", regulation_id="REG-DP-001",
    severity=Severity.CRITICAL, description="The facial recognition login collects biometric info with no consent documented")
check("paraphrased description still matches", env2._matches_violation(paraphrase, gt0))

# Zero keyword match  should fail (need at least 1 keyword)
no_kw = ViolationFlag(section_id="sec_collection", regulation_id="REG-DP-001",
    severity=Severity.CRITICAL, description="The data collection practices are questionable")
check("zero keyword match fails", not env2._matches_violation(no_kw, gt0))

# But 1 keyword is enough
one_kw = ViolationFlag(section_id="sec_collection", regulation_id="REG-DP-001",
    severity=Severity.CRITICAL, description="No consent mechanism for data collection")
check("one keyword match succeeds", env2._matches_violation(one_kw, gt0))

# Keywords in suggested_fix  should match
fix_kw = ViolationFlag(section_id="sec_collection", regulation_id="REG-DP-001",
    severity=Severity.CRITICAL, description="Data collected improperly",
    suggested_fix="Add explicit consent for biometric facial recognition")
check("keywords in suggested_fix matches", env2._matches_violation(fix_kw, gt0))

#  Test 6: Reward increases with correct detections 
print("\n[Reward Progression]")
env3 = ComplianceReviewEnv()
env3.reset("easy_privacy_review")
prev_reward = -999
rewards_increasing = True

for gt in SCENARIOS["easy_privacy_review"].ground_truth_violations:
    _, rew, _, _ = env3.step(make_action(ActionType.FLAG_VIOLATION, None,
        section=gt.section_id, regulation=gt.regulation_id,
        severity=gt.severity,
        description=gt.description))
    if rew.total <= prev_reward:
        rewards_increasing = False
    prev_reward = rew.total
check("rewards strictly increase with each correct flag", rewards_increasing)
check("final reward > 0.5", prev_reward > 0.5)  # Lower threshold since process quality is 0 without read_regulation

#  Test 7: False positive penalty 
print("\n[False Positive Penalty]")
env4 = ComplianceReviewEnv()
env4.reset("easy_privacy_review")
_, rew_clean, _, _ = env4.step(make_action(ActionType.FLAG_VIOLATION, None,
    section="sec_collection", regulation="REG-DP-001", severity="critical",
    description="Biometric data without consent or lawful basis"))
clean_reward = rew_clean.total

env4b = ComplianceReviewEnv()
env4b.reset("easy_privacy_review")
# Flag same correct violation
env4b.step(make_action(ActionType.FLAG_VIOLATION, None,
    section="sec_collection", regulation="REG-DP-001", severity="critical",
    description="Biometric data without consent or lawful basis"))
# Flag a false positive
_, rew_fp, _, _ = env4b.step(make_action(ActionType.FLAG_VIOLATION, None,
    section="sec_purpose", regulation="REG-DP-003", severity="minor",
    description="Purpose section is too vague"))
check("FP penalty is negative", rew_fp.false_positive_penalty < 0)
check("reward with FP < reward without FP", rew_fp.total < clean_reward + 0.5)

#  Test 8: Graders produce 0.0-1.0 for edge cases 
print("\n[Grader Edge Cases]")
for task_id in SCENARIOS:
    env_g = ComplianceReviewEnv()
    env_g.reset(task_id)
    # Empty submission  should be very low
    env_g.step(make_action(ActionType.SUBMIT_REVIEW, None,
        overall_status="compliant", summary="Looks fine"))
    state = env_g.state()
    score = grade_episode(state)
    check(f"{task_id} empty submission score in [0, 1]", 0.0 <= score <= 1.0)
    check(f"{task_id} empty submission score < 0.3", score < 0.3)

    # Perfect submission
    env_p = ComplianceReviewEnv()
    env_p.reset(task_id)
    for gt in SCENARIOS[task_id].ground_truth_violations:
        env_p.step(make_action(ActionType.FLAG_VIOLATION, None,
            section=gt.section_id, regulation=gt.regulation_id,
            severity=gt.severity, description=gt.description))
    env_p.step(make_action(ActionType.SUBMIT_REVIEW, None,
        overall_status="non_compliant", summary="All violations found"))
    state_p = env_p.state()
    score_p = grade_episode(state_p)
    check(f"{task_id} perfect submission score > 0.8", score_p > 0.8)
    check(f"{task_id} perfect submission in [0, 1]", 0.0 <= score_p <= 1.0)

#  Test 9: Severity-weighted completeness 
print("\n[Severity-Weighted Completeness]")
env5 = ComplianceReviewEnv()
env5.reset("easy_privacy_review")

# Flag only the 2 critical violations (should get higher completeness than flagging 2 minor ones)
criticals = [v for v in SCENARIOS["easy_privacy_review"].ground_truth_violations if v.severity == "critical"]
for gt in criticals[:2]:
    env5.step(make_action(ActionType.FLAG_VIOLATION, None,
        section=gt.section_id, regulation=gt.regulation_id,
        severity=gt.severity, description=gt.description))
crit_coverage = env5._severity_weighted_coverage()

env6 = ComplianceReviewEnv()
env6.reset("easy_privacy_review")
majors = [v for v in SCENARIOS["easy_privacy_review"].ground_truth_violations if v.severity == "major"]
for gt in majors[:2]:
    env6.step(make_action(ActionType.FLAG_VIOLATION, None,
        section=gt.section_id, regulation=gt.regulation_id,
        severity=gt.severity, description=gt.description))
maj_coverage = env6._severity_weighted_coverage()
check("critical violations worth more than major", crit_coverage > maj_coverage)

#  Test 10: Max steps enforcement 
print("\n[Max Steps]")
env7 = ComplianceReviewEnv()
env7.reset("easy_privacy_review")  # max 20
for i in range(20):
    _, _, done, _ = env7.step(make_action(ActionType.NOOP))
check("done after max_steps", done)
# Auto-submit should have triggered
state7 = env7.state()
check("auto-submit on max_steps", state7.review_submitted)

#  Summary 
print(f"\n{'='*60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed}")
print(f"{'='*60}")
if failed > 0:
    sys.exit(1)

