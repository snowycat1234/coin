from __future__ import annotations
import random
import numpy as np


def seed_all(seed: int) -> None:
    import torch
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    # Reproducibility is best-effort across hardware; CUDA bitwise identity not promised.


def build_model(name: str, d: int, nasset: int, length: int):
    import torch
    from torch import nn

    class TCN(nn.Module):
        def __init__(self):
            super().__init__()
            self.a = nn.Embedding(nasset, 16)
            self.c = nn.Sequential(nn.Conv1d(d, 128, 5, padding=2), nn.GELU(),
                                   nn.Conv1d(128, 128, 5, padding=2), nn.GELU(), nn.AdaptiveAvgPool1d(1))
            self.h = nn.Sequential(nn.Linear(144, 128), nn.GELU(), nn.Linear(128, 2))
        def forward(self, x, a):
            return self.h(torch.cat([self.c(x.transpose(1, 2)).squeeze(-1), self.a(a)], 1))

    class GRU(nn.Module):
        def __init__(self):
            super().__init__()
            self.a = nn.Embedding(nasset, 16)
            self.r = nn.GRU(d, 128, 2, batch_first=True, dropout=.1)
            self.h = nn.Linear(144, 2)
        def forward(self, x, a):
            return self.h(torch.cat([self.r(x)[0][:, -1], self.a(a)], 1))

    class Transformer(nn.Module):
        def __init__(self):
            super().__init__()
            self.a = nn.Embedding(nasset, 16)
            self.p = nn.Linear(d, 128)
            self.pos = nn.Parameter(torch.zeros(1, length, 128))
            nn.init.normal_(self.pos, std=.02)
            layer = nn.TransformerEncoderLayer(128, 4, 256, .1, batch_first=True, norm_first=True)
            self.e = nn.TransformerEncoder(layer, 3, enable_nested_tensor=False)
            self.h = nn.Linear(144, 2)
        def forward(self, x, a):
            z = self.p(x) + self.pos[:, :x.shape[1]]
            return self.h(torch.cat([self.e(z).mean(1), self.a(a)], 1))
    return {'TCN_SHARED': TCN, 'GRU_SHARED': GRU, 'TRANSFORMER_SHARED': Transformer}[name]()


def inner_split(items: list[tuple[int, str, int]], dates, label_ends: dict, embargo_days: int):
    """All inner validation and its label outcomes precede the outer fold."""
    import pandas as pd
    unique = sorted({i for _, _, i in items})
    if len(unique) < 20:
        return [], []
    cut = unique[int(len(unique) * .8)]
    boundary = dates[cut] - pd.Timedelta(days=embargo_days)
    train = [x for x in items if x[2] < cut and label_ends[x[1]][x[2]] < boundary]
    valid = [x for x in items if x[2] >= cut]
    return train, valid


def scaler_for(X: dict, items: list, length: int) -> tuple[np.ndarray, np.ndarray]:
    chunks = []
    for s in X:
        observed = np.zeros(len(X[s]), dtype=bool)
        for _, symbol, i in items:
            if symbol == s:
                observed[max(0, i - length + 1):i + 1] = True
        if observed.any():
            chunks.append(X[s][observed])
    if not chunks:
        raise ValueError('No training rows for scaler')
    z = np.concatenate(chunks)
    valid = np.isfinite(z)
    counts = valid.sum(0)
    mu = np.divide(np.where(valid, z, 0).sum(0), counts, out=np.zeros(z.shape[1]), where=counts > 0)
    var = np.divide(np.where(valid, (z - mu) ** 2, 0).sum(0), counts, out=np.ones(z.shape[1]), where=counts > 0)
    sd = np.sqrt(var)
    sd = np.where(np.isfinite(sd) & (sd > 1e-8), sd, 1.)
    return mu.astype('float32'), sd.astype('float32')


def transform(z: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    valid = np.isfinite(z)
    values = np.where(valid, (z - mu) / sd, 0.)
    return np.concatenate([values, valid.astype('float32')], axis=-1).astype('float32')


def fit_network(name, X, Y, train_items, predict_items, length, nasset, mu, sd, epochs,
                device, batch, seed, validation_items=None, patience=7, logger=print):
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, Dataset
    seed_all(seed)

    class Samples(Dataset):
        def __init__(self, rows):
            self.rows = rows
        def __len__(self):
            return len(self.rows)
        def __getitem__(self, j):
            sid, s, i = self.rows[j]
            x = transform(X[s][i - length + 1:i + 1], mu, sd)
            return torch.from_numpy(x), torch.tensor(sid), torch.tensor(Y[s][i], dtype=torch.float32)

    model = build_model(name, len(mu) * 2, nasset, length).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=7e-4, weight_decay=1e-3)
    lossfn = nn.SmoothL1Loss()
    loader = DataLoader(Samples(train_items), batch_size=batch, shuffle=True, num_workers=0)
    val = DataLoader(Samples(validation_items), batch_size=batch * 2, shuffle=False) if validation_items else None
    best, best_ep, saved, stale = float('inf'), epochs, None, 0
    for ep in range(1, epochs + 1):
        model.train()
        losses = []
        for x, a, y in loader:
            x, a, y = x.to(device), a.to(device), y.to(device)
            opt.zero_grad(set_to_none=True)
            loss = lossfn(model(x, a), y)
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite training loss')
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1); opt.step()
            losses.append(float(loss.detach().cpu()))
        logger(f'{name} epoch={ep}/{epochs} train_loss={np.mean(losses):.7g}')
        if val is not None:
            model.eval(); total, count = 0., 0
            with torch.no_grad():
                for x, a, y in val:
                    loss = lossfn(model(x.to(device), a.to(device)), y.to(device))
                    total += float(loss.cpu()) * len(y); count += len(y)
            score = total / count
            if score < best - 1e-7:
                best, best_ep, stale = score, ep, 0
                saved = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            else:
                stale += 1
            if stale >= patience:
                break
    if val is not None:
        if saved is None:
            raise ValueError('No finite inner-validation checkpoint')
        model.load_state_dict(saved)
    model.eval(); outputs = []
    with torch.no_grad():
        for x, a, _ in DataLoader(Samples(predict_items), batch_size=batch * 2, shuffle=False):
            outputs.append(model(x.to(device), a.to(device)).cpu().numpy())
    pred = np.concatenate(outputs) if outputs else np.empty((0, 2))
    return pred, best_ep, {k: v.detach().cpu() for k, v in model.state_dict().items()}
