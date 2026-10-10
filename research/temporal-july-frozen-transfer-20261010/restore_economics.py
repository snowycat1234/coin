"""Restore small source-bound economic members; never download exchange archives."""

import argparse
import hashlib
import json
import struct
import urllib.request
import zlib
from pathlib import Path

COMMIT = "5109edcaa5a790a023a11828cfd1452b5705ba1a"
BASE = f"https://raw.githubusercontent.com/snowycat1234/coin/{COMMIT}/research/core5-july2024-native-data/"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def restore(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    transferred = 0

    def fetch(path, left=None, right=None):
        nonlocal transferred
        headers = {} if left is None else {"Range": f"bytes={left}-{right - 1}"}
        with urllib.request.urlopen(
            urllib.request.Request(BASE + path, headers=headers), timeout=25
        ) as r:
            if left is not None and (
                r.status != 206
                or r.headers.get("Content-Range", "").split("/")[0] != f"bytes {left}-{right - 1}"
            ):
                raise ValueError(
                    "Exact partial response required; refuse whole archive/part download"
                )
            limit = 200000 if left is None else right - left
            data = r.read(limit + 1)
        if len(data) > limit or (left is not None and len(data) != limit):
            raise ValueError("Small exact response budget exceeded")
        transferred += len(data)
        return data

    consumer_bytes = fetch("CONSUMER_INDEX.json")
    consumer = json.loads(consumer_bytes)
    index_bytes = fetch("JULY2024/INDEX.json")
    index = json.loads(index_bytes)
    size, part_size = index["package_bytes"], index["maximum_part_bytes"]

    def package_range(left, right):
        if not 0 <= left < right <= size:
            raise ValueError("Range outside original wrapper")
        chunks = []
        while left < right:
            number, offset = divmod(left, part_size)
            end = min(right, (number + 1) * part_size)
            chunks.append(
                fetch("JULY2024/" + index["parts"][number]["name"], offset, offset + end - left)
            )
            left = end
        return b"".join(chunks)

    tail = package_range(size - 20000, size)
    at = tail.rfind(b"PK\x05\x06")
    if at < 0:
        raise ValueError("Small wrapper central directory required")
    end_record = struct.unpack_from("<4s4H2IH", tail, at)
    count, directory_size, directory_offset = end_record[4:7]
    if directory_size > 200000 or end_record[1:3] != (0, 0):
        raise ValueError("Unsupported ZIP layout")
    directory = package_range(directory_offset, directory_offset + directory_size)
    entries, offset = {}, 0
    for _ in range(count):
        row = struct.unpack_from("<4s6H3I5H2I", directory, offset)
        if row[0] != b"PK\x01\x02":
            raise ValueError("Central directory signature")
        name_len, extra_len, comment_len = row[10:13]
        name = directory[offset + 46 : offset + 46 + name_len].decode()
        entries[name] = dict(
            method=row[4], CRC32=row[7], compressed=row[8], bytes=row[9], offset=row[16]
        )
        offset += 46 + name_len + extra_len + comment_len
    expected = {r["path"]: r for r in consumer["economic_table_artifacts"]}
    expected["VALIDATION.json"] = next(
        r for r in index["members"] if r["name"] == "VALIDATION.json"
    )
    checked = {}
    for name, binding in expected.items():
        # Only these small derived economic members are admitted. No raw market ZIP.
        if (
            name != "VALIDATION.json"
            and name != "ECONOMICS.npz"
            and not name.startswith("normalized/")
        ):
            raise ValueError("Unadmitted member")
        entry = entries[name]
        header = package_range(entry["offset"], entry["offset"] + 30)
        fields = struct.unpack("<4s5H3I2H", header)
        if fields[0] != b"PK\x03\x04" or fields[3] != entry["method"]:
            raise ValueError("Local ZIP header identity")
        start = entry["offset"] + 30 + fields[-2] + fields[-1]
        encoded = package_range(start, start + entry["compressed"])
        data = encoded if entry["method"] == 0 else zlib.decompress(encoded, -15)
        if (
            len(data) != binding["bytes"]
            or sha(data) != binding["SHA256"]
            or zlib.crc32(data) != entry["CRC32"]
        ):
            raise ValueError("Derived member SHA/size/CRC mismatch: " + name)
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        checked[name] = dict(bytes=len(data), SHA256=sha(data), CRC32_verified=True)
    (output / "CONSUMER_INDEX.json").write_bytes(consumer_bytes)
    (output / "INDEX.json").write_bytes(index_bytes)
    receipt = dict(
        source_commit=COMMIT,
        consumer_index_SHA256=sha(consumer_bytes),
        part_index_SHA256=sha(index_bytes),
        restored=checked,
        response_body_bytes=transferred,
        provider_downloads=0,
        whole_archive_downloads=0,
        raw_market_members_restored=0,
        exact_HTTP206_ranges=True,
    )
    (output / "RESTORE_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({k: v for k, v in receipt.items() if k != "restored"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    restore(parser.parse_args().output)
