import argparse
from pathlib import Path

import torch

from .stage import prepare, train_slice

parser = argparse.ArgumentParser(
    description="Exactly one full773 fresh256 selected refit; no reserve access"
)
parser.add_argument("action", choices=("prepare", "worker"))
parser.add_argument("--state", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
(prepare if args.action == "prepare" else train_slice)(args.state, args.output)
