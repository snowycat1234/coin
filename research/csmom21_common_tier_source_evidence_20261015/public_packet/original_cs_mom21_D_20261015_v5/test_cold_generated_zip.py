"""Fresh-process, in-memory original ZIP shape. No stored source is opened.

Run this executable separately from the unittest suite so prior fake parsing
cannot warm the codec registry. --expect-cold-stop is the unmodified graph's
negative control; the normal invocation imports the exact repaired CLI first.
"""
import argparse
from io import BytesIO
import json
from pathlib import Path
import sys
import traceback
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-cold-stop', action='store_true')
    args = parser.parse_args()
    cold_cp437 = 'encodings.cp437' not in sys.modules
    if not cold_cp437:
        raise AssertionError('FRESH_PROCESS_WITH_COLD_CP437_REQUIRED')
    if not args.expect_cold_stop:
        import prepare_cs_source  # Same two exact preguard codec imports as CLI.
    import cs_source_bridge as bridge
    import cs_entry
    import cs_source
    import cs_signal
    import cs_quality
    from cs_source_guard import SourceOnlyGuard
    cs_signal.originals(); cs_signal.common_grid(); cs_quality.original_quality()
    # Literal BOM bytes. Encoding this fixture with utf-8-sig would warm the
    # dependency under test before the boundary and invalidate the cold proof.
    at = bridge.START
    row = [str(at // 1000), '10', '11', '9', '10', '5',
           str((at + bridge.MINUTE - 1000) // 1000), '50', '1', '0', '0', '0']
    payload = b'\xef\xbb\xbf' + (','.join(row) + '\n').encode('ascii')
    stream = BytesIO()
    info = zipfile.ZipInfo('BTCUSDT-1m-2022-01.csv')
    info.compress_type = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr(info, payload)
    assert info.flag_bits == 0 and info.compress_type == zipfile.ZIP_DEFLATED
    guard = SourceOnlyGuard()
    completed, failure = False, None
    try:
        with guard:
            try:
                rows, proof = bridge.parse_original_zip(stream.getvalue(), symbol='BTCUSDT',
                                                        period='2022-01', family='klines')
                assert rows == {at: tuple(row)} and proof['observed_minutes'] == 1
                completed = True
            except BaseException:
                failure = traceback.format_exc()
                raise
    except BaseException:
        if failure is None:
            failure = traceback.format_exc()
    if args.expect_cold_stop:
        assert not completed and guard.attempts['financial_imports'] == 1
        assert "filename.decode(self.metadata_encoding or 'cp437')" in failure
        assert all(not n for key, n in guard.attempts.items() if key != 'financial_imports')
    else:
        assert completed and failure is None and not any(guard.attempts.values())
    print(json.dumps(dict(schema='FRESH_GENERATED_BOM_ASCII_FLAG0_DEFLATED_ZIP_REGRESSION_V3',
        status='PASS', expected_cold_stop=args.expect_cold_stop, cp437_initially_cold=cold_cp437,
        literal_BOM_bytes=True, ZIP_member_flag_bits=info.flag_bits, ZIP_compression=info.compress_type,
        parser_completed=completed, forbidden_attempts=guard.attempts,
        actual_source_bodies_read=0, actual_source_scopes=0, financial_runs=0,
        traceback=failure), indent=2))


if __name__ == '__main__':
    main()
