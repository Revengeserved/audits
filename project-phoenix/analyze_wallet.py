from __future__ import annotations

import argparse
from pathlib import Path

from src.etherscan_client import EtherscanClient
from src.zerion_client import ZerionClient


def main():
    parser = argparse.ArgumentParser(description='Project Phoenix wallet analyzer')
    parser.add_argument('address', help='Public wallet address')
    args = parser.parse_args()

    print(f'== Project Phoenix ==')
    print(f'Analyzing: {args.address}')

    try:
        zerion = ZerionClient()
        portfolio = zerion.wallet_portfolio(args.address)
        print('✓ Zerion portfolio retrieved')
    except Exception as e:
        portfolio = None
        print(f'Zerion: {e}')

    try:
        etherscan = EtherscanClient()
        txs = etherscan.normal_transactions(args.address)
        erc20 = etherscan.erc20_transfers(args.address)
        print('✓ Etherscan history retrieved')
    except Exception as e:
        txs = erc20 = None
        print(f'Etherscan: {e}')

    report = Path('cases/case-001-0xe30e85/report.generated.md')
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(f'''# Generated Report\n\nAddress: {args.address}\n\nZerion: {portfolio is not None}\nEtherscan: {txs is not None}\n''')
    print(f'Report written to {report}')

if __name__ == '__main__':
    main()
