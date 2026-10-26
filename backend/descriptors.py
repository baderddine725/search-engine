"""
Descripteurs classiques calculés sur la base Objects (bdimage).

Chaque descripteur retourne un histogramme L1-normalisé (somme = 1), donc
comparable avec la distance L1 (Manhattan) ou chi-carré. Combiner plusieurs
descripteurs = concaténer des sous-histogrammes pondérés : la somme pondérée
de distances L1 reste une distance.

Descripteurs implémentés :
  - color    : histogramme HSV 8×4×4 (128 bins), robuste à la luminosité
  - lbp      : histogramme LBP uniform P=8 R=1 (10 bins), texture
  - hog      : HOG agrégé en 2×2 cellules × 9 orientations (36 bins), forme
"""

from typing import Dict, Iterable, Optional, Tuple

import numpy as np
from PIL import Image
from skimage.color import rgb2hsv
from skimage.feature import hog, local_binary_pattern

from config import LBP_RADIUS, LBP_N_POINTS, LBP_BINS

# ---------------------------------------------------------------------------
# Spécifications
# ---------------------------------------------------------------------------

DESCRIPTORS: Dict[str, Dict] = {
    "color": {
        "label": "Couleur (HSV 8×4×4)",
        "dims": 128,
        "description": "Histogramme HSV 8 bins H × 4 bins S × 4 bins V, L1-normalisé.",
    },
    "lbp": {
        "label": f"LBP uniform P={LBP_N_POINTS} R={LBP_RADIUS}",
        "dims": LBP_BINS,
        "description": "Local Binary Pattern uniforme, histogramme 10 bins.",
    },
    "hog": {
        "label": "HOG 2×2 cellules × 9 orientations",
        "dims": 36,
        "description": "Histogram of Oriented Gradients agrégé puis L1-normalisé.",
    },
}

RESIZE_TO = (128, 128)   # Taille commune (rapide, suffisant pour l'histogramme)


def _as_rgb(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGB").resize(RESIZE_TO), dtype=np.float32) / 255.0


def _l1_normalize(h: np.ndarray) -> np.ndarray:
    s = h.sum()
    return (h / s).astype(np.float32) if s > 0 else h.astype(np.float32)


# ---------------------------------------------------------------------------
# Descripteurs individuels
# ---------------------------------------------------------------------------

def color_hist(img: Image.Image) -> np.ndarray:
    hsv = rgb2hsv(_as_rgb(img))
    h, _ = np.histogramdd(
        hsv.reshape(-1, 3),
        bins=(8, 4, 4),
        range=((0, 1), (0, 1), (0, 1)),
    )
    return _l1_normalize(h.ravel())


def lbp_hist(img: Image.Image, resize: Optional[Tuple[int, int]] = RESIZE_TO) -> np.ndarray:
    """
    Histogramme LBP uniforme L1-normalisé (LBP_BINS bins). Implémentation unique,
    aussi utilisée par feature_extractor (InceptionV3 + LBP) avec resize=None,
    c'est-à-dire en pleine résolution.
    """
    gray = img.convert("L")
    if resize is not None:
        gray = gray.resize(resize)
    gray = np.asarray(gray)
    lbp = local_binary_pattern(gray, LBP_N_POINTS, LBP_RADIUS, method="uniform")
    hist, _ = np.histogram(
        lbp.ravel(),
        bins=LBP_BINS,
        range=(0, LBP_N_POINTS + 2),
    )
    return _l1_normalize(hist.astype(np.float32))


def hog_hist(img: Image.Image) -> np.ndarray:
    gray = np.asarray(img.convert("L").resize(RESIZE_TO), dtype=np.float32) / 255.0
    f = hog(
        gray,
        orientations=9,
        pixels_per_cell=(64, 64),        # 128 / 64 = 2 cellules par axe
        cells_per_block=(2, 2),
        block_norm="L1",
        feature_vector=True,
    )
    return _l1_normalize(f.astype(np.float32))


_FUNCS = {"color": color_hist, "lbp": lbp_hist, "hog": hog_hist}


def extract(img: Image.Image, name: str) -> np.ndarray:
    if name not in _FUNCS:
        raise ValueError(f"Descripteur inconnu : {name}")
    return _FUNCS[name](img)


# ---------------------------------------------------------------------------
# Combinaison de descripteurs
# ---------------------------------------------------------------------------

def combine(parts: Iterable[np.ndarray], weights: Iterable[float]) -> np.ndarray:
    """
    Concatène des sous-histogrammes pondérés : chaque sous-vecteur est multiplié
    par son poids avant concaténation. Avec la distance L1, la distance globale
    est alors la somme pondérée des distances L1 par descripteur.
    """
    parts = list(parts)
    weights = list(weights)
    if len(parts) != len(weights):
        raise ValueError("parts et weights doivent avoir la même longueur.")
    total = sum(weights) or 1.0
    return np.concatenate([
        (w / total) * p for p, w in zip(parts, weights)
    ]).astype(np.float32)


def combined_dims(names: Iterable[str]) -> int:
    return sum(DESCRIPTORS[n]["dims"] for n in names)
