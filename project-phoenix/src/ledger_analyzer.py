"""Project Phoenix ledger analyzer skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class LedgerFinding:
    category: str
    confidence_score: int
    evidence: str
    recommended_action: str


def classify_findings(rows: Iterable[dict]) -> list[LedgerFinding]:
    """Classify public ledger rows into recovery findings.

    This is a placeholder for the scoring engine. It should never invent data;
    every finding must be tied to a source row or documented evidence.
    """
    findings: list[LedgerFinding] = []
    for row in rows:
        notes = str(row.get("notes", "")).lower()
        if "airdrop" in notes or "claim" in notes:
            findings.append(
                LedgerFinding(
                    category="Airdrop or claim lead",
                    confidence_score=60,
                    evidence=str(row),
                    recommended_action="Review source transaction and claim status manually.",
                )
            )
    return findings
