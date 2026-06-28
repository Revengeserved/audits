from __future__ import annotations

import argparse
import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.etherscan_client import EtherscanClient
from src.zerion_client import ZerionClient

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
DEFAULT_CASES_DIR = Path("cases")


class SafeWriter:
    def __init__(self, case_dir: Path) -> None:
        self.case_dir = case_dir
        self.data_dir = case_dir / "data"
        self.report_dir = case_dir / "reports"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def json(self, name: str, payload: Any) -> Path:
        path = self.data_dir / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        return path

    def csv(self, name: str, rows: list[dict[str, Any]], columns: list[str]) -> Path:
        path = self.data_dir / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow({column: row.get(column, "") for column in columns})
        return path

    def markdown(self, name: str, text: str) -> Path:
        path = self.report_dir / name
        path.write_text(text, encoding="utf-8")
        return path


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def validate_address(address: str) -> str:
    address = address.strip()
    if not ADDRESS_RE.match(address):
        raise SystemExit(f"Invalid EVM address: {address}")
    return address


def case_slug(address: str, case_id: str | None) -> str:
    prefix = case_id or "case-auto"
    return f"{prefix}-{address[:10].lower()}"


def normalize_etherscan_rows(payload: dict[str, Any] | None, category: str) -> list[dict[str, Any]]:
    if not payload or not isinstance(payload, dict):
        return []
    result = payload.get("result", [])
    if not isinstance(result, list):
        return []

    rows: list[dict[str, Any]] = []
    for item in result:
        if not isinstance(item, dict):
            continue
        timestamp = item.get("timeStamp", "")
        date_time_utc = ""
        if str(timestamp).isdigit():
            date_time_utc = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
        rows.append(
            {
                "category": category,
                "transaction_id": item.get("hash", ""),
                "date_time_utc": date_time_utc,
                "block_number": item.get("blockNumber", ""),
                "sender": item.get("from", ""),
                "recipient": item.get("to", ""),
                "asset": item.get("tokenSymbol", "ETH" if category == "normal" else ""),
                "amount_raw": item.get("value", ""),
                "contract": item.get("contractAddress", ""),
                "method": item.get("methodId", ""),
                "function_name": item.get("functionName", ""),
                "notes": "",
            }
        )
    return rows


def score_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    keywords = {
        "claim": (65, "Possible claim or airdrop interaction"),
        "airdrop": (65, "Possible airdrop interaction"),
        "stake": (60, "Possible staking interaction"),
        "unstake": (65, "Possible staking recovery lead"),
        "bridge": (60, "Possible bridge or cross-chain activity"),
        "withdraw": (55, "Withdrawal or exit activity"),
        "deposit": (50, "Deposit or funding activity"),
        "swap": (45, "Swap activity"),
        "approve": (40, "Token approval; review permissions"),
    }
    seen: set[tuple[str, str]] = set()
    for row in rows:
        haystack = " ".join(str(row.get(k, "")) for k in ("function_name", "method", "notes", "contract", "asset")).lower()
        for keyword, (score, reason) in keywords.items():
            if keyword in haystack:
                key = (row.get("transaction_id", ""), reason)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    {
                        "confidence_score": score,
                        "category": reason,
                        "transaction_id": row.get("transaction_id", ""),
                        "date_time_utc": row.get("date_time_utc", ""),
                        "evidence": row.get("function_name") or row.get("method") or row.get("asset") or "Public ledger row",
                        "recommended_action": "Open the transaction in a block explorer and verify whether funds, rewards, permissions, or linked wallets require follow-up.",
                    }
                )
    return sorted(findings, key=lambda item: item["confidence_score"], reverse=True)


def build_report(address: str, case_name: str, files_written: list[Path], counts: dict[str, int], findings: list[dict[str, Any]], errors: list[str]) -> str:
    lines = [
        "# Project Phoenix Wallet Investigation Report",
        "",
        f"Generated: {now_utc()}",
        f"Case: `{case_name}`",
        f"Address: `{address}`",
        "",
        "## Executive Summary",
        "",
        "This is an automated first-pass public ledger review. It does not prove ownership, recover access, or verify private evidence. Treat all findings as leads requiring manual review.",
        "",
        "## Data Collection Status",
        "",
        f"- Normal transactions: {counts.get('normal', 0)}",
        f"- ERC-20 transfers: {counts.get('erc20', 0)}",
        f"- Combined public rows: {counts.get('combined', 0)}",
        f"- Scored findings: {len(findings)}",
        "",
        "## High Confidence Recovery Candidates",
        "",
    ]

    high = [f for f in findings if f["confidence_score"] >= 80]
    medium = [f for f in findings if 60 <= f["confidence_score"] < 80]
    low = [f for f in findings if 40 <= f["confidence_score"] < 60]

    def add_findings(items: list[dict[str, Any]]) -> None:
        if not items:
            lines.append("None detected by this automated pass.")
            lines.append("")
            return
        for item in items:
            lines.append(f"- **{item['confidence_score']}** — {item['category']} — `{item['transaction_id']}`")
            lines.append(f"  - Evidence: {item['evidence']}")
            lines.append(f"  - Recommended action: {item['recommended_action']}")
        lines.append("")

    add_findings(high)
    lines.extend(["## Medium Confidence Recovery Candidates", ""])
    add_findings(medium)
    lines.extend(["## Low Confidence Recovery Candidates", ""])
    add_findings(low)

    lines.extend(
        [
            "## Images Requiring Manual Review",
            "",
            "Pending user-provided evidence.",
            "",
            "## Documents Requiring Manual Review",
            "",
            "Pending user-provided evidence.",
            "",
            "## Potential Wallet Backup Files",
            "",
            "No private files scanned by this script. Keep sensitive recovery materials out of GitHub.",
            "",
            "## Potential Recovery Material Detected",
            "",
            "No private recovery material is collected or stored by this script.",
            "",
            "## Email Findings",
            "",
            "Pending Gmail or exported-email review.",
            "",
            "## Cloud Storage Findings",
            "",
            "Pending cloud export review.",
            "",
            "## Phone Storage Findings",
            "",
            "Pending device export review.",
            "",
            "## Recovery Priority Ranking",
            "",
        ]
    )

    if findings:
        for index, item in enumerate(findings[:20], start=1):
            lines.append(f"{index}. Score {item['confidence_score']} — {item['category']} — `{item['transaction_id']}`")
    else:
        lines.append("No scored leads detected yet.")

    lines.extend(["", "## Master Recovery Index", ""])
    lines.append("| File Name | Source | Type | Date Created | Date Modified | Confidence Score | Reason Flagged | Recommended Action |")
    lines.append("|---|---|---|---|---|---:|---|---|")
    for path in files_written:
        lines.append(f"| {path.name} | Local generated output | Evidence artifact | {now_utc()} | {now_utc()} | 0 | Generated by analyzer | Review and keep only non-sensitive public data in GitHub |")

    if errors:
        lines.extend(["", "## Collection Warnings", ""])
        for error in errors:
            lines.append(f"- {error}")

    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- Do not paste or commit seed phrases, private keys, keystore passwords, recovery cards, or live API keys.",
            "- Use `.env` locally and keep only `.env.example` in GitHub.",
            "- Public blockchain data can identify addresses and transaction history, but it does not prove wallet ownership.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Project Phoenix wallet analyzer")
    parser.add_argument("address", help="Public EVM wallet address")
    parser.add_argument("--case-id", default="case-001", help="Case identifier, e.g. case-001")
    parser.add_argument("--cases-dir", default=str(DEFAULT_CASES_DIR), help="Output cases directory")
    parser.add_argument("--skip-zerion", action="store_true", help="Skip Zerion collection")
    parser.add_argument("--skip-etherscan", action="store_true", help="Skip Etherscan collection")
    args = parser.parse_args()

    address = validate_address(args.address)
    name = case_slug(address, args.case_id)
    case_dir = Path(args.cases_dir) / name
    writer = SafeWriter(case_dir)

    print("== Project Phoenix ==")
    print(f"Case: {name}")
    print(f"Analyzing: {address}")

    files_written: list[Path] = []
    errors: list[str] = []
    rows: list[dict[str, Any]] = []

    if not args.skip_zerion:
        try:
            portfolio = ZerionClient().wallet_portfolio(address)
            files_written.append(writer.json("zerion-portfolio.json", portfolio))
            print("✓ Zerion portfolio retrieved")
        except Exception as exc:
            errors.append(f"Zerion collection skipped or failed: {exc}")
            print(f"Zerion: {exc}")

    normal_payload = None
    erc20_payload = None
    if not args.skip_etherscan:
        try:
            etherscan = EtherscanClient()
            normal_payload = etherscan.normal_transactions(address)
            erc20_payload = etherscan.erc20_transfers(address)
            files_written.append(writer.json("etherscan-normal-transactions.json", normal_payload))
            files_written.append(writer.json("etherscan-erc20-transfers.json", erc20_payload))
            print("✓ Etherscan history retrieved")
        except Exception as exc:
            errors.append(f"Etherscan collection skipped or failed: {exc}")
            print(f"Etherscan: {exc}")

    rows.extend(normalize_etherscan_rows(normal_payload, "normal"))
    rows.extend(normalize_etherscan_rows(erc20_payload, "erc20"))

    transaction_columns = [
        "category",
        "transaction_id",
        "date_time_utc",
        "block_number",
        "sender",
        "recipient",
        "asset",
        "amount_raw",
        "contract",
        "method",
        "function_name",
        "notes",
    ]
    files_written.append(writer.csv("combined-public-ledger.csv", rows, transaction_columns))

    findings = score_rows(rows)
    finding_columns = ["confidence_score", "category", "transaction_id", "date_time_utc", "evidence", "recommended_action"]
    files_written.append(writer.csv("recovery-findings.csv", findings, finding_columns))

    report = build_report(
        address=address,
        case_name=name,
        files_written=files_written,
        counts={"normal": len(normalize_etherscan_rows(normal_payload, "normal")), "erc20": len(normalize_etherscan_rows(erc20_payload, "erc20")), "combined": len(rows)},
        findings=findings,
        errors=errors,
    )
    report_path = writer.markdown("report.generated.md", report)
    files_written.append(report_path)

    print(f"✓ Combined rows: {len(rows)}")
    print(f"✓ Scored findings: {len(findings)}")
    print(f"✓ Report written to {report_path}")


if __name__ == "__main__":
    main()
