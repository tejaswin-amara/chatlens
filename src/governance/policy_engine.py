"""Action governance and tiered Human-In-The-Loop (HITL) policy engine.

Enforces three strict Risk Tiers:
- Tier 0: Read-only / Safe operations (auto-execute in all modes)
- Tier 1: Reversible mutations (auto-execute in live mode with undo receipt)
- Tier 2: Destructive / High-impact mutations (mandate interactive human approval with 24h TTL)
"""

from __future__ import annotations

import enum
import hashlib
import hmac
import time
from dataclasses import dataclass

from src.governance.guards import UntrustedInput


class ActionTier(enum.StrEnum):
    """Risk tiers for all agent operations."""

    TIER_0_READ = "TIER_0_READ"
    TIER_1_REVERSIBLE = "TIER_1_REVERSIBLE"
    TIER_2_HIGH_RISK = "TIER_2_HIGH_RISK"


class PolicyVerdict(enum.StrEnum):
    """Policy authorization outcomes."""

    ALLOWED = "ALLOWED"
    CONFIRMATION_PENDING = "CONFIRMATION_PENDING"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class PolicyEvaluationResult:
    """Outcome of a policy evaluation."""

    verdict: PolicyVerdict
    tier: ActionTier
    intent: str
    action_description: str
    reason: str
    requires_approval: bool
    state_token: str


class PolicyEngine:
    """Enforces execution safety gates before dispatching to external APIs."""

    SECRET_SALT = b"spark-governance-v1"

    @classmethod
    def generate_state_token(cls, event_data: str, timestamp: float) -> str:
        """Create a cryptographic HMAC-SHA256 signature validating action integrity."""
        message = f"{event_data}:{timestamp}".encode()
        return hmac.new(cls.SECRET_SALT, message, hashlib.sha256).hexdigest()

    @classmethod
    def verify_state_token(cls, event_data: str, timestamp: float, token: str) -> bool:
        """Verify HMAC-SHA256 signature against event payload."""
        expected = cls.generate_state_token(event_data, timestamp)
        return hmac.compare_digest(expected, token)

    @classmethod
    def classify_action_tier(
        cls,
        intent: str,
        source: str = "regex",
    ) -> ActionTier:
        """Categorize operation into Tier 0 (Read), Tier 1 (Reversible), or Tier 2 (High Risk)."""
        intent_upper = (intent or "").upper()

        # Tier 0: Read operations
        if intent_upper in (
            "READ",
            "QUERY",
            "TIMETABLE_VIEW",
            "ATTENDANCE_VIEW",
            "STATUS_CHECK",
            "HELP",
            "UNKNOWN",
        ):
            return ActionTier.TIER_0_READ

        # Tier 1: Reversible mutations (tasks, deadlines, reminders)
        if intent_upper in ("TASK", "EXAM_DEADLINE", "REMINDER"):
            return ActionTier.TIER_1_REVERSIBLE

        # Tier 2: High-impact schedule, holiday, room overrides, class cancellations, ERP mutations
        if intent_upper in ("ROOM_OVERRIDE", "HOLIDAY", "CLASS_CANCELLED", "ERP_WRITE"):
            return ActionTier.TIER_2_HIGH_RISK

        return ActionTier.TIER_2_HIGH_RISK

    @classmethod
    def evaluate(
        cls,
        untrusted_input: UntrustedInput,
        intent: str,
        source: str = "regex",
        timetable_validated: bool = True,
        spark_mode: str = "confirm",
        action_payload: str = "",
    ) -> PolicyEvaluationResult:
        """Evaluate policy gates and determine action authorization."""
        ts = time.time()
        token = cls.generate_state_token(action_payload or intent, ts)
        tier = cls.classify_action_tier(intent, source)

        # Gate 0: Quarantined input is never executed
        if untrusted_input.quarantined:
            return PolicyEvaluationResult(
                verdict=PolicyVerdict.QUARANTINED,
                tier=tier,
                intent=intent,
                action_description="Execution blocked due to prompt injection quarantine",
                reason=untrusted_input.quarantine_reason or "Input quarantined",
                requires_approval=False,
                state_token=token,
            )

        # Gate 1: Tier 0 Read-Only operations auto-execute across all modes
        if tier == ActionTier.TIER_0_READ:
            return PolicyEvaluationResult(
                verdict=PolicyVerdict.ALLOWED,
                tier=tier,
                intent=intent,
                action_description="Read-only operation permitted",
                reason="Tier 0 safe read operation",
                requires_approval=False,
                state_token=token,
            )

        # Gate 2: Dry run mode rejects all external writes
        if spark_mode == "dry":
            return PolicyEvaluationResult(
                verdict=PolicyVerdict.REJECTED,
                tier=tier,
                intent=intent,
                action_description="Dry-run audit mode active",
                reason="Writes disabled in dry mode",
                requires_approval=False,
                state_token=token,
            )

        # Gate 3: High-impact events ALWAYS require human approval
        if intent.upper() in ("HOLIDAY", "CLASS_CANCELLED") or source == "gemini":
            return PolicyEvaluationResult(
                verdict=PolicyVerdict.CONFIRMATION_PENDING,
                tier=ActionTier.TIER_2_HIGH_RISK,
                intent=intent,
                action_description=f"Human approval required for {intent} (source: {source})",
                reason="Critical schedule mutation mandates interactive human sign-off",
                requires_approval=True,
                state_token=token,
            )

        # Gate 4: Tier 2 ROOM_OVERRIDE policy
        if tier == ActionTier.TIER_2_HIGH_RISK and intent.upper() == "ROOM_OVERRIDE":
            if spark_mode == "live" and source == "regex" and timetable_validated:
                return PolicyEvaluationResult(
                    verdict=PolicyVerdict.ALLOWED,
                    tier=tier,
                    intent=intent,
                    action_description="Auto-approved regex room override",
                    reason="Validated regex room override permissible in live mode",
                    requires_approval=False,
                    state_token=token,
                )
            return PolicyEvaluationResult(
                verdict=PolicyVerdict.CONFIRMATION_PENDING,
                tier=tier,
                intent=intent,
                action_description="Room override pending human confirmation",
                reason="Room override requires owner ✅ confirmation",
                requires_approval=True,
                state_token=token,
            )

        # Gate 5: Tier 1 Reversible mutations (TASK / EXAM_DEADLINE)
        if tier == ActionTier.TIER_1_REVERSIBLE:
            if spark_mode == "live" and source == "regex":
                return PolicyEvaluationResult(
                    verdict=PolicyVerdict.ALLOWED,
                    tier=tier,
                    intent=intent,
                    action_description="Auto-approved regex task creation",
                    reason="Reversible regex task creation permissible in live mode",
                    requires_approval=False,
                    state_token=token,
                )
            return PolicyEvaluationResult(
                verdict=PolicyVerdict.CONFIRMATION_PENDING,
                tier=tier,
                intent=intent,
                action_description="Task creation pending human confirmation",
                reason="Task write requires owner ✅ confirmation in confirm mode",
                requires_approval=True,
                state_token=token,
            )

        # Default fallback
        return PolicyEvaluationResult(
            verdict=PolicyVerdict.CONFIRMATION_PENDING,
            tier=tier,
            intent=intent,
            action_description="Action requires human review",
            reason="Conservative policy fallback",
            requires_approval=True,
            state_token=token,
        )


policy_engine = PolicyEngine()
