"""
VP-Tree (Vantage-Point Tree) — partitionnement métrique de l'espace des descripteurs.

Chaque nœud choisit un point de vue (vantage point) et la médiane mu des distances
des points du sous-ensemble à ce point : les points à distance < mu vont à gauche
(boule intérieure), les autres à droite. La recherche k-NN élague un sous-arbre dès
que l'inégalité triangulaire garantit qu'il ne peut contenir de point plus proche
que le k-ième voisin courant (tau).

Implémentation par tableaux (sérialisable en .npz, partageable entre workers) :
  - les vecteurs X restent dans leur ordre d'origine (souvent un np.memmap) ;
  - perm      : permutation des indices, chaque feuille est une tranche contiguë ;
  - nœuds     : vp, mu, left, right, start, end (start/end = tranche de perm).
Distance : L1 (Manhattan), métrique recommandée par MPEG-7 pour les histogrammes,
et pour laquelle la somme pondérée de descripteurs reste une métrique.
"""

import heapq
import time

import numpy as np

LEAF_SIZE = 64


def l1(X: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Distances L1 entre chaque ligne de X et q."""
    return np.abs(X - q).sum(axis=1)


class VPTree:
    def __init__(self, X, perm, vp, mu, left, right, start, end):
        self.X = X
        self.perm, self.vp, self.mu = perm, vp, mu
        self.left, self.right, self.start, self.end = left, right, start, end

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def build(cls, X: np.ndarray, leaf_size: int = LEAF_SIZE, seed: int = 0,
              chunk: int = 200_000) -> "VPTree":
        rng = np.random.default_rng(seed)
        n = X.shape[0]
        perm = np.arange(n, dtype=np.int64)
        vp, mu, left, right, start, end = [], [], [], [], [], []

        def new_node(s, e):
            vp.append(-1); mu.append(0.0); left.append(-1); right.append(-1)
            start.append(s); end.append(e)
            return len(vp) - 1

        root = new_node(0, n)
        stack = [root]
        while stack:
            node = stack.pop()
            s, e = start[node], end[node]
            if e - s <= leaf_size:
                continue
            idx = perm[s:e]
            v = idx[rng.integers(e - s)]
            q = np.asarray(X[v], dtype=np.float32)
            d = np.empty(e - s, dtype=np.float32)
            for i in range(0, e - s, chunk):  # par blocs : mémoire bornée
                d[i:i + chunk] = l1(np.asarray(X[idx[i:i + chunk]], dtype=np.float32), q)
            m = float(np.median(d))
            inner = d < m
            n_in = int(inner.sum())
            if n_in == 0 or n_in == e - s:
                # Distances toutes égales (doublons) : partage arbitraire en deux
                order = np.argsort(d, kind="stable")
                n_in = (e - s) // 2
                m = float(d[order[n_in]])
            else:
                order = np.concatenate([np.flatnonzero(inner), np.flatnonzero(~inner)])
            perm[s:e] = idx[order]
            vp[node], mu[node] = int(v), m
            lft, rgt = new_node(s, s + n_in), new_node(s + n_in, e)
            left[node], right[node] = lft, rgt
            stack.extend([lft, rgt])

        arr = lambda a, t: np.asarray(a, dtype=t)
        return cls(X, perm, arr(vp, np.int64), arr(mu, np.float32),
                   arr(left, np.int32), arr(right, np.int32),
                   arr(start, np.int64), arr(end, np.int64))

    # ------------------------------------------------------------------
    # Persistance
    # ------------------------------------------------------------------
    def save(self, path: str):
        np.savez(path, perm=self.perm, vp=self.vp, mu=self.mu, left=self.left,
                 right=self.right, start=self.start, end=self.end)

    @classmethod
    def load(cls, path: str, X) -> "VPTree":
        z = np.load(path)
        return cls(X, z["perm"], z["vp"], z["mu"], z["left"], z["right"],
                   z["start"], z["end"])

    @property
    def n_nodes(self) -> int:
        return len(self.vp)

    # ------------------------------------------------------------------
    # Recherche k-NN (exacte, ou approchée si max_leaves est fixé)
    # ------------------------------------------------------------------
    def search(self, q: np.ndarray, k: int = 10, exclude: int = -1,
               max_leaves: int = 0) -> tuple:
        """
        Retourne ([(distance, indice)] triés par distance croissante, stats).
        exclude : indice à ignorer (l'image requête elle-même).
        max_leaves : 0 = recherche exacte ; sinon nombre maximal de feuilles visitées.
        """
        t0 = time.perf_counter()
        q = np.asarray(q, dtype=np.float32)
        heap = []  # max-heap (-d, i) des k meilleurs
        tau = np.inf
        computed = leaves = 0
        # File de priorité sur la borne inférieure de distance de chaque sous-arbre
        todo = [(0.0, 0)]
        while todo:
            bound, node = heapq.heappop(todo)
            if bound > tau:
                break
            if self.left[node] < 0:  # feuille
                idx = self.perm[self.start[node]:self.end[node]]
                d = l1(np.asarray(self.X[idx], dtype=np.float32), q)
                computed += len(idx)
                leaves += 1
                for dist, i in zip(d.tolist(), idx.tolist()):
                    if i == exclude:
                        continue
                    if len(heap) < k:
                        heapq.heappush(heap, (-dist, i))
                    elif dist < -heap[0][0]:
                        heapq.heapreplace(heap, (-dist, i))
                if len(heap) == k:
                    tau = -heap[0][0]
                if max_leaves and leaves >= max_leaves:
                    break
                continue
            v = int(self.vp[node])
            dv = float(np.abs(np.asarray(self.X[v], dtype=np.float32) - q).sum())
            computed += 1
            # Le point de vue appartient aussi à une feuille : il n'est compté que là
            # (sinon il occuperait deux places parmi les k voisins).
            m = float(self.mu[node])
            # Inégalité triangulaire : borne inférieure de d(q, x) dans chaque boule
            heapq.heappush(todo, (max(bound, dv - m, 0.0), int(self.left[node])))
            heapq.heappush(todo, (max(bound, m - dv, 0.0), int(self.right[node])))
        res = sorted((-nd, i) for nd, i in heap)
        n = self.X.shape[0]
        # Comparaisons effectives (bornée par n : les points de vue croisés deux fois
        # — comme nœud interne puis comme élément de leur feuille — ne comptent qu'une).
        effective = min(computed, n)
        return res, {
            "index": "vptree",
            "distances_computed": effective,
            "leaves_visited": leaves,
            "pruned_pct": round(100.0 * (1 - effective / n), 2) if n else 0.0,
            "search_ms": (time.perf_counter() - t0) * 1000,
        }


def linear_search(X, q: np.ndarray, k: int = 10, exclude: int = -1,
                  chunk: int = 200_000) -> tuple:
    """Recherche séquentielle exhaustive (référence pour mesurer le gain du VP-Tree)."""
    t0 = time.perf_counter()
    q = np.asarray(q, dtype=np.float32)
    n = X.shape[0]
    best_d, best_i = np.empty(0, np.float32), np.empty(0, np.int64)
    for s in range(0, n, chunk):
        d = l1(np.asarray(X[s:s + chunk], dtype=np.float32), q)
        i = np.arange(s, s + len(d))
        if 0 <= exclude - s < len(d):
            d[exclude - s] = np.inf
        kk = min(k, len(d))
        top = np.argpartition(d, kk - 1)[:kk]
        best_d = np.concatenate([best_d, d[top]])
        best_i = np.concatenate([best_i, i[top]])
    order = np.argsort(best_d, kind="stable")[:k]
    res = [(float(best_d[j]), int(best_i[j])) for j in order if np.isfinite(best_d[j])]
    return res, {
        "index": "linear",
        "distances_computed": n,
        "leaves_visited": 0,
        "pruned_pct": 0.0,
        "search_ms": (time.perf_counter() - t0) * 1000,
    }
