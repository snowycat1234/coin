# Restore saved results without rerunning accounts

The complete 25-member result packet is stored as fourteen UTF-8 chunks public/RESULTS_00.b64 through RESULTS_13.b64. Concatenate in numeric filename order, base64-decode to RESULTS.zip, then verify the byte length and SHA256 in RESULTS_PACKET_INDEX.json before extraction into a new directory. Verify all member byte lengths and SHA256 and ZIP CRC. Original inputs, targets, ten saved quantity traces, paired bootstrap indices/samples, protocol, publication record and independent Decimal audit sources are included.

The separate targets/PROOF.json files are in TARGETS.zip, also available through public/TARGETS_0.b64 through TARGETS_3.b64. TARGETS_PACKET_INDEX.json records all four members.

COLD_RESTORE_QA.json records independent local restored-byte validation of all ten saved wallets and bootstrap samples without account advancement, target generation, providers or RNG. Full original source remains in this Git history. No result from a rerun is needed to inspect or recover this module.

REPORT.md and ATTRIBUTION.md retain negative findings; MIX_EXPLANATION.md explains why raw-signal 50:50 is not equal capital allocation. Known development history only, not a live strategy qualification.
