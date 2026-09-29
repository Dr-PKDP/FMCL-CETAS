"""
CIFAR-10 federated partitioner. Mirrors realdata/real_data.py's
make_real_federated_data() exactly in interface and partitioning
semantics (same alpha meaning, same with-replacement class sampling,
same client (X, y) tuple format), so it slots into the existing
methodology without changing what "alpha" or "n_per" mean anywhere else
in the paper.

CIFAR-10 itself: 50,000 32x32x3 RGB training images, 10 classes,
downloaded once via torchvision and cached locally.
"""
import numpy as np


def _load_cifar10(data_dir="./cifar_cache"):
    """
    Returns (X, y): X as float32 (N, 3, 32, 32) in [0, 1], y as int (N,).
    Downloads once; torchvision caches under data_dir on subsequent runs.
    """
    import torchvision

    ds = torchvision.datasets.CIFAR10(root=data_dir, train=True, download=True)
    X = ds.data.astype(np.float32) / 255.0          # (50000, 32, 32, 3)
    X = np.transpose(X, (0, 3, 1, 2)).copy()          # -> (N, 3, 32, 32)
    y = np.array(ds.targets, dtype=int)
    return X, y


def make_cifar_federated_data(N=100, n_per=50, alpha=0.3, seed=0,
                               data_dir="./cifar_cache"):
    """
    Same signature pattern as real_data.make_real_federated_data, with
    dataset fixed to CIFAR-10. Returns (clients, K, shape) where clients
    is a list of N (X_i, y_i) tuples, K=10, shape=(3,32,32) -- shape
    replaces real_data's flat `dim` since images are not flattened here.
    """
    rng = np.random.default_rng(seed)
    X, y = _load_cifar10(data_dir)
    K = 10

    by_class = [np.where(y == k)[0] for k in range(K)]
    min_pool = min(len(c) for c in by_class)
    if min_pool == 0:
        raise RuntimeError("a class has zero examples in the CIFAR-10 pool")

    props = rng.dirichlet([alpha] * K, size=N)

    clients = []
    for i in range(N):
        counts = rng.multinomial(n_per, props[i])
        X_parts, y_parts = [], []
        for k in range(K):
            if counts[k] > 0:
                chosen = rng.choice(by_class[k], size=counts[k], replace=True)
                X_parts.append(X[chosen])
                y_parts.extend([k] * counts[k])
        Xc = np.concatenate(X_parts, axis=0) if X_parts else np.zeros((0, 3, 32, 32), dtype=np.float32)
        yc = np.array(y_parts, dtype=int)
        clients.append((Xc, yc))

    return clients, K, (3, 32, 32)
