"""Explicit future full-path optimizer interface; no fitting on import or check."""

from __future__ import annotations

import time

import torch

from .checkpoint import load_checkpoint, make_optimizer, run_binding, run_guard, save_checkpoint
from .exact import training_loss, verify_prototype


def train_steps(
    model,
    episodes,
    prototype,
    directory,
    *,
    max_steps,
    feature_batch_size=32,
    checkpoint_every=1,
    max_seconds=120.0,
):
    """Only a caller's explicit invocation starts economic fitting.

    Use the existing authorized bounded resource launcher. Fixed terminal step,
    no validation selection. Default save is every completed full-path update.
    A restarted process loads the latest generation rather than starting over.
    Model must be reconstructed with the original seeded initialization/scaler
    before calling this function, so initial snapshot identity can be checked.
    """
    episodes = tuple(episodes)
    if model.mean.device.type != "cpu" or not episodes or any(e.role != "TRAIN" for e in episodes):
        raise ValueError("Complete training-only episodes and CPU selector required")
    normalizer = model.normalization_provenance
    if normalizer.get("training_cutoff_us") != episodes[0].split_cutoff_us or normalizer.get(
        "training_window_identities"
    ) != [e.windows.identity for e in episodes]:
        raise ValueError("Shared standardizer must bind precisely these training feature windows")
    verify_prototype(prototype)
    data = dict(
        episodes=[e.identity for e in episodes],
        roles=[e.role for e in episodes],
        split_cutoff_us=[e.split_cutoff_us for e in episodes],
    )
    binding = run_binding(
        model,
        data_split_identity=data,
        feature_batch_size=feature_batch_size,
        max_steps=max_steps,
        checkpoint_every=checkpoint_every,
        max_seconds=max_seconds,
    )
    optimizer = make_optimizer(model)
    with run_guard(directory, binding) as output:
        if (output / "latest.json").exists():
            state = load_checkpoint(output, model, optimizer, binding)
            step, prior_elapsed = state["step"], state["elapsed_seconds"]
        else:
            torch.manual_seed(model.seed + 3)
            model.train()
            step, prior_elapsed = 0, 0.0
            save_checkpoint(output, model, optimizer, binding, step=0)
        began = time.monotonic()
        while step < max_steps:
            if prior_elapsed + time.monotonic() - began >= max_seconds:
                raise TimeoutError(
                    "Bound total training time exhausted; retain last completed checkpoint"
                )
            model.train()
            optimizer.zero_grad(set_to_none=True)
            loss = training_loss(model, episodes, prototype, feature_batch_size=feature_batch_size)
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite full-path objective; preserve last checkpoint")
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            step += 1
            elapsed = prior_elapsed + time.monotonic() - began
            if step % checkpoint_every == 0 or step == max_steps or elapsed >= max_seconds:
                save_checkpoint(
                    output, model, optimizer, binding, step=step, elapsed_seconds=elapsed
                )
            print(
                dict(
                    stage="full_path_training",
                    completed_steps=step,
                    total_steps=max_steps,
                    training_loss=float(loss.detach()),
                    gradient_norm=float(norm),
                    elapsed_seconds=elapsed,
                ),
                flush=True,
            )
        return dict(
            status="FIXED_TRAINING_STEPS_COMPLETE",
            completed_steps=step,
            run_id=binding["run_id"],
            validation_scored=False,
        )
