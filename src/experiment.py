"""Test Number Five: experience-dependent cable transfer spectroscopy.

Toy physics, not biological data. Requires NumPy. Run from repo root:
    python -m src.experiment
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np

N_BRANCHES = 4
DEPTH = 6
N = 1 + N_BRANCHES * DEPTH
TIPS = np.array([b * DEPTH + DEPTH for b in range(N_BRANCHES)], dtype=int)
FREQ = np.array([.05, .1, .2, .4, .8, 1.6, 3.2, 6.4])
FORECAST_FREQ = FREQ[:5]
WRITE_BUDGET = .65
EPS = 1e-12
TRAIN_SEEDS = range(40)
TEST_SEEDS = range(40, 80)


@dataclass(frozen=True)
class Cable:
    G: np.ndarray  # axial graph Laplacian plus membrane leak (positive definite)
    C: np.ndarray  # membrane capacitance, diagonal entries
    edges: tuple[tuple[int, int, float], ...]
    leak: np.ndarray


def cable(seed: int) -> Cable:
    rng = np.random.default_rng(seed + 10001)
    C = rng.uniform(.82, 1.18, size=N)
    leak = rng.uniform(.11, .18, size=N)
    leak[0] = .27
    G = np.diag(leak.copy())
    edges = []
    for arm in range(N_BRANCHES):
        prev = 0
        for d in range(1, DEPTH + 1):
            node = 1 + arm * DEPTH + (d - 1)
            g = float(rng.uniform(.85, 1.15))
            G[prev, prev] += g
            G[node, node] += g
            G[prev, node] -= g
            G[node, prev] -= g
            edges.append((prev, node, g))
            prev = node
    return Cable(G=G, C=C, edges=tuple(edges), leak=leak)


def experience_eligibility(model: Cable, branch: int) -> np.ndarray:
    """A unit impulse and free relaxation. Integrated squared voltage is local eligibility.

    The location is a controlled experimental assignment, not a label inserted
    into memory. Only the dynamics of the resulting voltage write the shunt.
    """
    v = np.zeros(N)
    v[TIPS[branch]] = 1.0 / model.C[TIPS[branch]]
    eligibility = np.zeros(N)
    dt = .025
    for _ in range(360):
        eligibility += dt * v * v
        v += dt * (-model.G @ v / model.C)
    return eligibility


def after_experience(model: Cable, branch: int, budget: float = WRITE_BUDGET) -> tuple[Cable, np.ndarray]:
    eligibility = experience_eligibility(model, branch)
    update = budget * eligibility / eligibility.sum()
    return Cable(
        G=model.G + np.diag(update), C=model.C,
        edges=model.edges, leak=model.leak + update,
    ), update


def transfers(model: Cable, freqs: np.ndarray = FREQ) -> np.ndarray:
    """Complex frequency response: [freq, probe tip], observed only at soma."""
    B = np.eye(N, dtype=complex)[:, TIPS]
    out = np.empty((len(freqs), len(TIPS)), dtype=complex)
    for k, w in enumerate(freqs):
        out[k] = np.linalg.solve(model.G + 1j * w * np.diag(model.C), B)[0]
    return out


def delta_log_amplitude(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    return np.log(np.abs(after) + EPS) - np.log(np.abs(before) + EPS)


def native_basis(model: Cable, rank: int = 8) -> np.ndarray:
    invsqrt = 1 / np.sqrt(model.C)
    S = (invsqrt[:, None] * model.G) * invsqrt[None, :]
    vals, vecs = np.linalg.eigh(S)
    assert np.all(vals > 0)
    return invsqrt[:, None] * vecs[:, :rank]


def index_cosine_basis(model: Cable, rank: int = 8) -> np.ndarray:
    """Index DCT-II with C-normalization; *not* the cable's own eigenmodes."""
    j = np.arange(N)[:, None]
    k = np.arange(rank)[None, :]
    V = np.cos(np.pi * (j + .5) * k / N)
    V[:, 0] *= 1 / np.sqrt(2)
    V *= np.sqrt(2 / N)
    return V / np.sqrt(model.C[:, None])


def projected_transfers(model: Cable, V: np.ndarray, freqs: np.ndarray = FORECAST_FREQ) -> np.ndarray:
    GT = V.T @ model.G @ V
    CT = V.T @ (model.C[:, None] * V)
    B = V[TIPS, :].T
    out = np.empty((len(freqs), len(TIPS)), dtype=complex)
    for i, w in enumerate(freqs):
        out[i] = V[0] @ np.linalg.solve(GT + 1j * w * CT, B)
    return out


def ridge_fit_predict(Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray, alpha: float = 1.) -> np.ndarray:
    """Fixed ridge multiclass linear readout. No hyperparameter search."""
    mu = Xtr.mean(axis=0)
    sd = Xtr.std(axis=0)
    sd = np.where(sd < 1e-9, 1, sd)
    a = (Xtr - mu) / sd
    b = (Xte - mu) / sd
    onehot = np.eye(N_BRANCHES)[ytr]
    A = np.concatenate([a, np.ones((len(a), 1))], axis=1)
    B = np.concatenate([b, np.ones((len(b), 1))], axis=1)
    reg = np.diag([alpha] * a.shape[1] + [0.])
    weight = np.linalg.solve(A.T @ A + reg, A.T @ onehot)
    return np.argmax(B @ weight, axis=1)


def build_dataset() -> dict:
    features, unpaired, labels, seeds, sham, nonzero = [], [], [], [], [], []
    forecast_native, forecast_dct = [], []
    no_write_errors = []
    for seed in range(80):
        model = cable(seed)
        pre = transfers(model)
        no_write_errors.append(float(np.max(np.abs(pre - transfers(model)))))
        native = native_basis(model)
        cosine = index_cosine_basis(model)
        after_samples = []
        for branch in range(N_BRANCHES):
            updated, _ = after_experience(model, branch)
            h = transfers(updated)
            after_samples.append(h)
            delta = delta_log_amplitude(pre, h)
            features.append(delta.T.ravel())  # tip-major for slicing single-port
            unpaired.append(np.log(np.abs(h.T).ravel() + EPS))
            labels.append(branch)
            seeds.append(seed)
            nonzero.append(np.sqrt(np.mean(delta * delta)))
            if seed in TEST_SEEDS:
                target = h[:len(FORECAST_FREQ)]
                native_pred = projected_transfers(updated, native)
                dct_pred = projected_transfers(updated, cosine)
                # pointwise relative absolute errors, fixed epsilon scale.
                scale = np.abs(target) + 1e-9
                forecast_native.extend((np.abs(native_pred - target) / scale).ravel().tolist())
                forecast_dct.extend((np.abs(dct_pred - target) / scale).ravel().tolist())
        # Random, label-independent sham using a reproducible second random stream.
        # No association of assigned branch label with the actual physical write.
        rng = np.random.default_rng(seed + 810100)
        for branch in range(N_BRANCHES):
            independent_actual_branch = int(rng.integers(0, N_BRANCHES))
            h_sham = after_samples[independent_actual_branch]
            sham.append(delta_log_amplitude(pre, h_sham).T.ravel())
    return {
        'paired': np.asarray(features), 'unpaired': np.asarray(unpaired),
        'sham': np.asarray(sham), 'labels': np.asarray(labels),
        'seeds': np.asarray(seeds), 'delta_rms': np.asarray(nonzero),
        'forecast_native': np.asarray(forecast_native),
        'forecast_dct': np.asarray(forecast_dct),
        'no_write_errors': np.asarray(no_write_errors),
    }


def gates(data: dict) -> dict:
    split = data['seeds'] < 40
    y = data['labels']
    def accuracy(name: str, X: np.ndarray) -> float:
        prediction = ridge_fit_predict(X[split], y[split], X[~split])
        return float(np.mean(prediction == y[~split]))
    paired = accuracy('paired', data['paired'])
    unpaired = accuracy('unpaired', data['unpaired'])
    single = accuracy('single', data['paired'][:, :len(FREQ)])
    sham = accuracy('sham', data['sham'])
    native_median = float(np.median(data['forecast_native']))
    dct_median = float(np.median(data['forecast_dct']))
    result = {
        'setup': {'seed_train': '0-39', 'seed_test': '40-79', 'n_test': int(np.sum(~split)),
                  'modes': 8, 'write_budget': WRITE_BUDGET, 'probe_frequencies_rad_s': FREQ.tolist()},
        'measurements': {
            'trace_fraction_above_threshold': float(np.mean(data['delta_rms'] >= .01)),
            'median_trace_rms': float(np.median(data['delta_rms'])),
            'no_write_max_transfer_error': float(np.max(data['no_write_errors'])),
            'paired_accuracy': paired, 'unpaired_accuracy': unpaired,
            'single_port_accuracy': single, 'sham_accuracy': sham,
            'native_median_relative_error': native_median,
            'index_cosine_median_relative_error': dct_median,
            'native_to_cosine_error_ratio': native_median / max(dct_median, 1e-30),
        },
    }
    m = result['measurements']
    result['gates'] = {
        'G1': m['trace_fraction_above_threshold'] >= .90 and m['no_write_max_transfer_error'] <= 1e-10,
        'G2': paired >= .75 and paired - unpaired >= .10,
        'G3': m['native_to_cosine_error_ratio'] <= .70,
        'G4': sham <= .40,
        'G5': paired - single >= .10,
    }
    result['notes'] = [
        'Toy demonstration only: write rule was explicitly constructed to be experience-sensitive.',
        'Frequencies are temporal angular frequencies (rad/s), not semantic frequency bands.',
        'No genuine plasticity is claimed for a frozen transformer, nor biological validation for this cable.',
        'Relative spectral approximation error may be unstable for tiny distal transfer amplitudes; raw error distributions are saved.',
    ]
    return result


def plots(data: dict, output: Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(14, 4))
    base = cable(42)
    h0 = transfers(base)
    b1, change = after_experience(base, 1)
    h1 = transfers(b1)
    for arm in range(4):
        axs[0].semilogx(FREQ, np.abs(h0[:, arm]), '--', alpha=.5)
        axs[0].semilogx(FREQ, np.abs(h1[:, arm]), label=f'probe arm {arm}')
    axs[0].set(title='One soma: before (dashes) / after (solid)', xlabel='angular frequency (rad/s)', ylabel='|H|')
    axs[0].legend(fontsize=8)
    for arm in range(4):
        axs[1].semilogx(FREQ, delta_log_amplitude(h0, h1)[:, arm], '-o', label=f'probe {arm}')
    axs[1].axhline(0, color='gray', linewidth=.6)
    axs[1].set(title='Experience response fingerprint', xlabel='angular frequency (rad/s)', ylabel='change in log |H|')
    axs[2].bar(np.arange(N), change)
    axs[2].set(title='Local membrane shunt update', xlabel='cable compartment', ylabel='added leak (matched total)')
    fig.suptitle('Test Number Five — operator response after experience (synthetic)', fontsize=13)
    fig.tight_layout()
    fig.savefig(output, dpi=145)
    plt.close(fig)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='results')
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    data = build_dataset()
    report = gates(data)
    (out / 'gates.json').write_text(json.dumps(report, indent=2) + '\n')
    np.savez_compressed(out / 'arrays.npz', **data)
    try:
        plots(data, out / 'spectroscopy.png')
    except ImportError:
        print('matplotlib not installed: skipped figure')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
