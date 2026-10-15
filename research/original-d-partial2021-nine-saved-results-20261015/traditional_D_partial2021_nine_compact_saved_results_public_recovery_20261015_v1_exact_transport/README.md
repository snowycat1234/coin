# Exact unchanged ZIP transport

These two binary parts transport the exact independently reviewed compact ZIP without changing, repacking or recompressing any archive byte. The whole ZIP is deliberately not uploaded as one blob. Download both parts from this same immutable publication commit, then concatenate part001 followed by part002, without decoding, decompression or inserting newlines. Save as traditional_D_partial2021_nine_compact_saved_results_public_recovery_20261015_v1.zip.

Expected archive bytes: 12342661. Expected SHA256: 2caf85dde33db4a1ac31e04cec830ec6df72a1e6029e2e4b32b093d869e85c1a. Check both before opening. TRANSPORT_MANIFEST.json pins the ordered part sizes and hashes. The two parts are 8388608 and 3954053 bytes. The 131 expanded members are separately published, and their exact bytes match the recovered archive members with passing CRCs.

After recovery, extract into an empty directory and follow the packet README for saved-only validation. This transport does not supply omitted full MINUTE/source/target/covariance arrays, recover their bytes from hashes, or grant financial-run, publication, source-download or policy authority. All compact packet qualifications remain unchanged.
