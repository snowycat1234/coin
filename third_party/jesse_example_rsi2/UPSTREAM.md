# Fixed public RSI2 and official RSI dependency

All upstream code and license files here preserve the downloaded bytes. Local
integration is `scripts/investment/public_rsi2_indicator.py`; no RSI recurrence,
Wilder averaging, initialization seed, or constant-price rule is implemented
locally. The strategy adapter uses the original public long entry and exit
hooks with the project's common allocation and execution constraints.

## Sources and licenses

- [jesse-ai/example-strategies](https://github.com/jesse-ai/example-strategies/tree/7c91e0a37bf62165790120d730442e4f6eb00364/RSI2),
  commit `7c91e0a37bf62165790120d730442e4f6eb00364`, MIT:
  `rsi2_original.py` and `LICENSE`.
- [jesse-ai/jesse](https://github.com/jesse-ai/jesse/tree/417f8765225e3bfc12043d4b712f19fe15a3c078),
  commit `417f8765225e3bfc12043d4b712f19fe15a3c078`, MIT:
  `rsi_indicator_original.py`, `JESSE_HELPERS_ORIGINAL.py`,
  `JESSE_CONFIG_ORIGINAL.py`, `JESSE_CONSTANTS_ORIGINAL.py`,
  `JESSE_REQUIREMENTS_ORIGINAL.txt`, and `JESSE_LICENSE`.
- [jesse-rust 1.3.0](https://pypi.org/project/jesse-rust/1.3.0/),
  [official repository](https://github.com/jesse-ai/jesse-rust), MIT:
  `rsi_kernel_original.rs` preserves the entire official source member
  `jesse_rust-1.3.0/src/oscillators.rs` from the checksum-bound sdist.
  `KERNEL_LICENSE` and `KERNEL_CARGO_ORIGINAL.toml` preserve the corresponding
  package files. Fixed Jesse requirements explicitly specify
  `jesse-rust==1.3.0`; no alternate indicator implementation is substituted.

## Runtime and semantics

The checksum-bound CPython 3.12 manylinux x86_64 wheel is installed with
`uv pip install --no-deps --target` into a separate D-backed WSL STATE directory.
The original clean environment and `environments/v8/uv.lock` remain unchanged.
No market data, models, GPU, account credentials, or trading service is required.
`INSTALLED_KERNEL_BINDING_20261002_V1.json` binds the package version, wheel,
sdist, original sources, installed package files, compiled extension, and base
environment lock. Binary and environment files stay outside Git.

The thin indicator compiles the original `get_candle_source`, `slice_candles`,
and `rsi` function AST nodes and original candle-column mapping in an isolated
namespace. The only configuration substitution fixes Jesse's documented source
default `env.data.warmup_candles_num=240`; the pinned default config has no
override. No original function body changes.

For a two-dimensional candle array, the upstream nonsequential scalar call
uses the last 240 bars. One-dimensional source calls do not slice. The
sequential full-source array is a different API and must not replace the
two-dimensional scalar call in the strategy. Kernel-defined NaNs for one or
two bars, empty scalar `IndexError`, flat/upward RSI 100, and downward RSI 0
are preserved. Input nonfinite closes are refused at the adapter boundary.

## Actual evidence and failed attempts

`RSI2_OFFICIAL_KERNEL_DEPENDENCY_INSTALL_20261002_V1.json` records the actual
SSL handshake timeout. V2 records an actual incorrect assumed `rsi.rs` archive
member assertion; the payloads had downloaded successfully. Neither failed
run establishes ABI compatibility. V3 reuses those verified payloads, selects
the actual exact `src/oscillators.rs` member, and installs the official wheel
with actual exit 0.

`RSI2_OFFICIAL_KERNEL_SEMANTICS_20261002_V1.json` records the sole synthetic
semantic run with actual exit 0, Python 3.12.3 and NumPy 2.5.3. It covers the
known seed, undefined inputs, official flat and monotone behavior, the original
240-bar scalar call, input immutability, future append causality, and unchanged
prebound source/environment bytes. This is dependency and synthetic indicator
evidence; it makes no market performance or native Jesse execution claim.

Wheel SHA256:
`65c0e9edd3af5397642ca417da2ef7c23f311d6fa2bf6a2d46c729f656528cee`.
Sdist SHA256:
`9609ec6b74aeccaf2889f8bdc5551cdc0fe0d093e0c657f8b1629f7dbc1600e1`.
The complete source pins and compiled extension SHA256 are in the binding and
`public_rsi2_indicator.PINNED_HASHES` / `kernel_receipt()`.
