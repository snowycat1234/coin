"""Use the accepted recovery boundary with unchanged V2 monthly orchestration."""
from pathlib import Path

from quant.paths import ROOT
from quant.research_fast.trade_flow_v2 import checksum, private_module, require

V2_SHA = 'a0dc0e120b1de90f35a1bb17f6dd8a4bebe42bb381f076f5f1a96450a3a6614c'
RECOVERY_STORE = ROOT/'data/research_fast/trade_flow_5s_v2_monthly_v7/recovery_20261002_v3'


def main():
    path = ROOT/'scripts/research_v7/fetch_monthly_v2.py'
    require(checksum(path) == V2_SHA, 'Unchanged accepted V2 source required')
    module = private_module('v8_monthly_recovered_prior_v2', path)
    # V2's local alias only supplies V1's prior manifest lookup.  V1.STORE and
    # source_view.MONTHLY_STORE retain their original November publication root.
    module.MONTHLY_STORE = RECOVERY_STORE
    factory = module.private_module

    def boundary_source_binding(name, target):
        value = factory(name, target)
        if Path(target) == ROOT/'scripts/research_v7/fetch_monthly.py':
            original = value.source_hashes
            value.source_hashes = lambda: {
                **original(), 'scripts/research_v8/fetch_monthly_from_recovery.py': checksum(Path(__file__))}
        return value

    module.private_module = boundary_source_binding
    module.main()


if __name__ == '__main__':
    main()
