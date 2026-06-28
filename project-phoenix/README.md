# Project Phoenix

Project Phoenix is the master crypto recovery and wallet-forensics workspace.

This repository section is designed to organize wallet investigations, recovery evidence, API tooling, and case reports without exposing seed phrases, private keys, or live API secrets.

## Structure

```text
project-phoenix/
├── README.md
├── .env.example
├── cases/
│   └── case-001-0xe30e85/
│       ├── notes.md
│       ├── transactions.csv
│       └── report.md
├── docs/
│   ├── master-recovery-prompt.md
│   └── recovery-scoring.md
└── src/
    ├── zerion_client.py
    ├── etherscan_client.py
    └── ledger_analyzer.py
```

## Modules

- **Project Ledger** — blockchain forensic investigations and wallet case files.
- **Wallet Recovery** — recovery artifacts, backup discovery, derivation-path analysis.
- **Airdrop Discovery** — historical and current eligibility research.
- **Asset Recovery Index** — tokens, NFTs, LP positions, staking, bridges, and hidden/dust assets.
- **Evidence Archive** — screenshots, exports, emails, logs, and cloud/device findings.
- **Recovery Roadmap** — priority ranking, blockers, and completed recoveries.
- **Research & Documentation** — APIs, wallet documentation, chain documentation, and procedures.

## Security Rules

Never commit:

- Seed phrases
- Private keys
- Keystore passwords
- Recovery cards
- Live `.env` files
- Full wallet exports containing sensitive secrets
- Unredacted API keys

Use `.env.example` for placeholders only.
