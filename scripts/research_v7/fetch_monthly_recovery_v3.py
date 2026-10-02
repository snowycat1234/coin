"""Independent recovery namespace; reuse unchanged V2 orchestration and converter."""
from pathlib import Path
from quant.paths import ROOT
from quant.research_fast.trade_flow_v2 import checksum, private_module, require
from source_view import MONTHLY_STORE

V2_SHA = "a0dc0e120b1de90f35a1bb17f6dd8a4bebe42bb381f076f5f1a96450a3a6614c"

def main():
    path=ROOT/'scripts/research_v7/fetch_monthly_v2.py'
    require(checksum(path)==V2_SHA,'Unchanged prior V2 orchestration required')
    module=private_module('v7_independent_recovery_v2',path)
    factory=module.private_module
    def recovery_namespace(name, target):
        value=factory(name,target)
        if Path(target)==ROOT/'scripts/research_v7/fetch_monthly.py':
            original=value.source_hashes
            value.source_hashes=lambda: {**original(),
                'scripts/research_v7/fetch_monthly_recovery_v3.py':checksum(Path(__file__))}
            value.STORE=MONTHLY_STORE/'recovery_20261002_v3'
        return value
    module.private_module=recovery_namespace
    module.main()

if __name__=='__main__':main()
