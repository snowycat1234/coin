"""Copy a root reviewed, ready manifest into one exclusive STATE directory."""
import hashlib, json, sys
from pathlib import Path
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state')
source=Path(sys.argv[1]);dest=Path(sys.argv[2])
assert source.resolve().is_relative_to(root) and source.stat().st_size<2_000_000
value=json.loads(source.read_bytes());assert value['ready_to_execute'] is True
assert dest.parent.parent==state and dest.name=='ACTUAL_BINDING.json' and not dest.parent.exists()
dest.parent.mkdir();dest.write_bytes(source.read_bytes())
print(json.dumps(dict(path=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),market_arrays_read=False)))
