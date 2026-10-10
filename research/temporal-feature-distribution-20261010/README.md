# Frozen input-scale diagnostic

Read-only, no new model training, wallet, scaler fit or policy output. The normalization buffers are the common original 907-row training scaler. Distinct input-row groups are original907, added2021's428 (62 overlap; 366 unique additions), July126, Q4 155. No missing masks are removed.

Observed feature cells beyond 5 old standard deviations: original0.286%, added2021 5.671%, July0%, Q4 1.290%. Added2021 mom200 maximum206.09 old standard deviations. The extreme is DOGE, completed May8 2021: close0.691522 versus 200-day-prior0.002593, a simple return265.688. It matches the archived feature to float32 precision; not classified as a corrupt tick and not deleted.

The expanded1137 frozen GRU has candidate tanh preactivation |x|>4 in9.390% of valid added2021 window/asset/unit/time positions versus0.191% on original training windows. Reset/update sigmoid |x|>8 fractions are3.997%/3.409% in added2021 versus0.0153%/0.0120% in original windows. Overlapping positions are not independent samples. These are descriptive saturation measurements, not proof of causality or universal vanishing gradients. Manual recurrent equations match the unchanged Torch GRU terminal states within2e-15 on all fully observed windows; learned model identities remain unchanged.

The original common scaler was deliberately held fixed to isolate the effect of adding historical economic data. These findings motivate one subsequent training-union normalization ablation, not a retrospective alteration of the completed comparison. No clipping, winsorization or removal of crisis observations is proposed.
