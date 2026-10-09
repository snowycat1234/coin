"""One shared exact prototype fixture per test process."""

import pytest
import torch

from .exact import load_prototype, prepare_recovery


@pytest.fixture(scope="session", autouse=True)
def deterministic_cpu():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


@pytest.fixture(scope="session")
def recovery(tmp_path_factory):
    return prepare_recovery(tmp_path_factory.mktemp("recovery") / "exact")


@pytest.fixture(scope="session")
def prototype(recovery):
    return load_prototype(recovery / "source/modules/direct_path/prototype.py")
