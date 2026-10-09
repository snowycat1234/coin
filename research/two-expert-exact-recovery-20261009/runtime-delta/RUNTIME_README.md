# Bounded recovery runtime

Use the exact recovery ZIP in this branch, extract it as a workspace, then overlay the files in runtime-delta at the same relative paths. Commands resolve inputs relative to that workspace. This delta changes only source-verification provenance and the resource launcher; original head, path objective, gradients, adapter, training NPZ files and original checkpoint bytes remain pinned.

The historical e5_inputs and conditional_selector_core source bodies are explicitly unavailable in this native executor. They are not imported by the fitting computation. Current byte verification is reported separately from the historical source identity used by the original checkpoint metadata. The recovered regime_ranking_screen body is verified against its historical SHA. No missing body is claimed verified.

Run from the extracted source directory:

    python bounded_recovery.py --report ../ADEQUACY_RESOURCES.json --seconds 120 python -m modules.native_action.two_expert_recovery_runtime continue --pack ../direct_path_fragments --index-sha256 e4fecc49cd1bb05f72dc0f8d24e793a5d7e4d2436c89a18bd9d7c625a7849be8 --frozen-fit ../two_expert_direct_fit --output ../two_expert_direct_adequacy_fit

Both original 64-step coefficient arrays must reproduce exactly before either arm takes a new optimizer step. Training-only checkpoint losses govern one continuation per arm; no feature, seed, architecture, objective or learning-rate changes are allowed. Both terminal heads are frozen before validation. Recovery bindings accompany the original computational receipts and must be verified before native consumers load either model under bound_runtime(). No native account replay is performed by this command.
