from __future__ import annotations
import contextlib
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
# Policy is deliberately not a user-configurable environment bypass.
LOCKED_START = date(2026, 3, 1)
LOCKED_END = date(2026, 9, 1)  # end exclusive; do not inspect archived bytes in this range
DAY_MS = 86_400_000
MINUTE_MS = 60_000
EXEC_OFFSET_US = 60_000_001  # completed day -> next day's 00:01:00.000001 proxy execution
CODE_VERSION = 'collector-v3.2-parallel-20261006'


def load_config(path: Path | None = None) -> None:
    path = path or Path(os.environ.get('CONFIG_FILE', ROOT / 'config.env'))
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key):
            raise ValueError(f'Invalid config key in {path}: {line!r}')
        tokens = shlex.split(value, comments=True)
        if len(tokens) > 1:
            raise ValueError(f'Config values containing spaces must be quoted: {key}')
        os.environ.setdefault(key, tokens[0] if tokens else '')


load_config()
WORK = Path(os.environ.get('WORK_DIR', ROOT / 'work')).expanduser().resolve()
DATA = WORK / 'data'
REPORTS = WORK / 'reports'
MODELS = WORK / 'models'
RAW = Path(os.environ.get('RAW_CACHE_DIR', DATA / 'raw')).expanduser().resolve()


def E(key: str, default: Any = None) -> str:
    value = os.environ.get(key, default)
    if value is None:
        raise ValueError(f'Missing configuration: {key}')
    return str(value)


def log(message: str) -> None:
    print(f'[{datetime.now(timezone.utc).isoformat(timespec="seconds")}] {message}', flush=True)


def init_dirs() -> None:
    for p in (DATA, REPORTS, MODELS, RAW, WORK / 'state', WORK / 'logs'):
        p.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def dump(value: Any, path: Path) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, default=str, allow_nan=False) + '\n')


def symbols() -> list[str]:
    result = [s.strip() for s in E('SYMBOLS').split(',') if s.strip()]
    if not result or len(result) != len(set(result)) or any(not re.fullmatch('[A-Z0-9]{2,30}', s) for s in result):
        raise ValueError('SYMBOLS must be unique uppercase Binance instrument codes')
    return result


def months(a: date, b: date) -> Iterator[tuple[int, int]]:
    y, m = a.year, a.month
    while (y, m) <= (b.year, b.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def bounds() -> tuple[date, date]:
    a, b = date.fromisoformat(E('WARMUP_START')), date.fromisoformat(E('END_DATE'))
    scoring = date.fromisoformat(E('START_DATE'))
    if not a <= scoring <= b:
        raise ValueError('Need WARMUP_START <= START_DATE <= END_DATE')
    # Monthly archives also contain bytes outside a partial month's requested slice.
    # Reject any request whose monthly payload intersects the locked interval.
    if a < LOCKED_END and b >= LOCKED_START:
        raise ValueError('LOCKED DATA: 2026-03-01..2026-08-31 is not authorized for this collector/research')
    if b >= datetime.now(timezone.utc).date():
        raise ValueError('END_DATE must be a completed UTC day, not today or the future')
    if E('RAW_INTERVAL') != '1m':
        raise ValueError('This audited minute schema supports RAW_INTERVAL=1m only')
    symbols()
    validate_options()
    return a, b



def validate_options() -> None:
    """Fail before network activity for invalid bounds/resource settings."""
    families = [x.strip() for x in E('FAMILIES').split(',')]
    allowed = {'klines', 'markPriceKlines', 'premiumIndexKlines', 'fundingRate'}
    if len(families) != len(set(families)) or not set(families) <= allowed or not {'klines', 'markPriceKlines', 'fundingRate'} <= set(families):
        raise ValueError('FAMILIES must include klines, markPriceKlines, fundingRate with no unknown/duplicate names')
    if families != E('FAMILIES').split(','):
        raise ValueError('Do not put whitespace inside FAMILIES')
    for key in ('LOOKBACK_DAYS', 'HORIZON_DAYS', 'MIN_HISTORY_DAYS', 'MIN_TRAIN_ASSET_ROWS', 'NUM_THREADS', 'BATCH_SIZE', 'EPOCHS', 'PATIENCE'):
        if int(E(key)) <= 0:
            raise ValueError(f'{key} must be a positive integer')
    for key in ('EMBARGO_DAYS', 'HTTP_RETRIES'):
        if int(E(key)) < 0:
            raise ValueError(f'{key} must be a nonnegative integer')
    if not 1 <= int(E('DOWNLOAD_WORKERS', '16')) <= 64:
        raise ValueError('DOWNLOAD_WORKERS must be between 1 and 64')
    for key in ('INITIAL_CAPITAL', 'MAX_WORK_GIB', 'MAX_ARCHIVE_MIB', 'MAX_UNCOMPRESSED_MIB', 'HTTP_CONNECT_TIMEOUT', 'HTTP_READ_TIMEOUT'):
        value = float(E(key))
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f'{key} must be finite and positive')
    if not 0 <= float(E('MIN_FREE_GIB')) < float(E('MAX_WORK_GIB')):
        raise ValueError('Need 0 <= MIN_FREE_GIB < MAX_WORK_GIB')
    if not 0 < float(E('ASSET_CAP')) <= .30 or not 0 < float(E('GROSS_CAP')) <= .60:
        raise ValueError('This package does not authorize increasing 30% single / 60% gross caps')
    if not 0 < float(E('LABEL_WEIGHT')) <= float(E('ASSET_CAP')):
        raise ValueError('LABEL_WEIGHT must be positive and no larger than ASSET_CAP')
    for key in ('DAILY_FALLBACK', 'REFRESH_CHECKSUMS'):
        if E(key) not in ('0', '1'):
            raise ValueError(f'{key} must be 0 or 1')
    side_cost()


def funding_scale() -> float:
    try:
        scale = float(E('FUNDING_RATE_SCALE'))
    except ValueError:
        raise ValueError('Funding unit is unconfirmed. Explicitly set FUNDING_RATE_SCALE=1.0 or 0.01 for a CONDITIONAL scenario; collector needs neither.') from None
    if scale not in (1.0, 0.01):
        raise ValueError('Only predeclared conditional funding scales 1.0 / 0.01 are supported')
    return scale


def side_cost() -> float:
    values = [float(E(k)) for k in ('FEE_BP_PER_SIDE', 'HALF_SPREAD_BP_PER_SIDE', 'SLIPPAGE_BP_PER_SIDE')]
    if any(not 0 <= v <= 1000 for v in values):
        raise ValueError('Invalid cost components in basis points')
    return sum(values) * 1e-4


def owned_bytes(root: Path) -> int:
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink()) if root.exists() else 0


def disk_guard(extra_bytes: int = 0, *, scan: bool = True) -> None:
    init_dirs()
    minimum = float(E('MIN_FREE_GIB')) * 2**30
    for p in {WORK, RAW}:
        if shutil.disk_usage(p).free - extra_bytes < minimum:
            raise RuntimeError(f'Disk reserve would be breached at {p}; keep {minimum/2**30:g} GiB free')
    if scan:
        total = owned_bytes(WORK)
        if not RAW.is_relative_to(WORK):
            total += owned_bytes(RAW)
        if total + extra_bytes > float(E('MAX_WORK_GIB')) * 2**30:
            raise RuntimeError('MAX_WORK_GIB budget reached; files retained, no automatic deletion')


def code_digest() -> str:
    h = hashlib.sha256()
    for p in sorted((ROOT / 'pipeline').glob('*.py')):
        h.update(p.name.encode()); h.update(p.read_bytes())
    return h.hexdigest()


def research_config() -> dict[str, str]:
    # Only public, relevant knobs: never serialize proxy URLs, credentials or all env.
    keys = '''SYMBOLS WARMUP_START START_DATE END_DATE RAW_INTERVAL FAMILIES TABLE_FORMAT LOOKBACK_DAYS HORIZON_DAYS MIN_HISTORY_DAYS MIN_TRAIN_ASSET_ROWS EMBARGO_DAYS LABEL_WEIGHT GROSS_CAP ASSET_CAP INITIAL_CAPITAL FEE_BP_PER_SIDE HALF_SPREAD_BP_PER_SIDE SLIPPAGE_BP_PER_SIDE FUNDING_RATE_SCALE MODEL_FAMILIES DEVICE NUM_THREADS BATCH_SIZE EPOCHS PATIENCE SEED'''.split()
    return {k: E(k) for k in keys}


@contextlib.contextmanager
def exclusive_lock() -> Iterator[None]:
    import fcntl
    init_dirs()
    with (WORK / '.pipeline.lock').open('a+') as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another pipeline is using this WORK_DIR; no duplicate run started') from None
        yield


def progress(stage: str, current: int, total: int, detail: str = '') -> None:
    dump(dict(stage=stage, current=current, total=total, detail=detail, pid=os.getpid(),
              observed_utc=datetime.now(timezone.utc).isoformat()), WORK / 'state' / 'progress.json')
