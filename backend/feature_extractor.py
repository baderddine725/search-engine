"""Extraction de caractéristiques visuelles (InceptionV3 + LBP, VGG16)."""

import io

import numpy as np
import requests
from PIL import Image
from tensorflow.keras.applications import InceptionV3, VGG16
from tensorflow.keras.applications import inception_v3, vgg16
from tensorflow.keras.preprocessing.image import img_to_array

from config import (
    IMG_SIZE,
    VGG16_IMG_SIZE,
    MODELS,
)
from descriptors import lbp_hist


# ----------------------------------------------------------------------
# Chargement des images
# ----------------------------------------------------------------------

def load_image_from_path(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")


def load_image_from_bytes(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def load_image_from_url(url: str) -> Image.Image:
    resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return load_image_from_bytes(resp.content)


class BaseExtractor:
    """Interface commune : extract(img) → vecteur numpy."""

    def extract(self, img: Image.Image) -> np.ndarray:
        raise NotImplementedError

    def extract_from_path(self, path: str) -> np.ndarray:
        """Extrait les features depuis un chemin fichier."""
        return self.extract(load_image_from_path(path))

    def extract_from_bytes(self, data: bytes) -> np.ndarray:
        """Extrait les features depuis des bytes (upload)."""
        return self.extract(load_image_from_bytes(data))

    def extract_from_url(self, url: str) -> np.ndarray:
        """Extrait les features depuis une URL d'image."""
        return self.extract(load_image_from_url(url))


class FeatureExtractor(BaseExtractor):
    """Pipeline d'extraction CNN (InceptionV3) + LBP."""

    def __init__(self):
        self.model = InceptionV3(
            weights="imagenet",
            include_top=False,
            pooling="avg",
            input_shape=(*IMG_SIZE, 3),
        )

    # ------------------------------------------------------------------
    # Extraction CNN
    # ------------------------------------------------------------------
    def _extract_cnn(self, img: Image.Image) -> np.ndarray:
        """Retourne un vecteur CNN de dimension 2048."""
        img_resized = img.resize(IMG_SIZE)
        arr = img_to_array(img_resized)
        arr = np.expand_dims(arr, axis=0)
        arr = inception_v3.preprocess_input(arr)
        features = self.model.predict(arr, verbose=0)
        return features.flatten()

    # ------------------------------------------------------------------
    # Extraction LBP
    # ------------------------------------------------------------------
    def _extract_lbp(self, img: Image.Image) -> np.ndarray:
        """Retourne un histogramme LBP normalisé de dimension LBP_BINS (pleine résolution)."""
        return lbp_hist(img, resize=None)

    # ------------------------------------------------------------------
    # Extraction combinée
    # ------------------------------------------------------------------
    def extract(self, img: Image.Image) -> np.ndarray:
        """Concatène CNN (2048) + LBP (10) → vecteur de 2058 dims."""
        cnn = self._extract_cnn(img)
        lbp = self._extract_lbp(img)
        return np.concatenate([cnn, lbp])


class VGG16Extractor(BaseExtractor):
    """Approche de référence : VGG16 pré-entraîné, global average pooling (512)."""

    def __init__(self):
        self.model = VGG16(
            weights="imagenet",
            include_top=False,
            pooling="avg",
            input_shape=(*VGG16_IMG_SIZE, 3),
        )

    def extract(self, img: Image.Image) -> np.ndarray:
        arr = img_to_array(img.resize(VGG16_IMG_SIZE))
        arr = vgg16.preprocess_input(np.expand_dims(arr, axis=0))
        return self.model.predict(arr, verbose=0).flatten()


# ----------------------------------------------------------------------
# Registre (chargement paresseux, un modèle par processus)
# ----------------------------------------------------------------------

_EXTRACTOR_CLASSES = {
    "inception_lbp": FeatureExtractor,
    "vgg16": VGG16Extractor,
}
_extractors = {}


def get_extractor(model: str) -> BaseExtractor:
    if model not in MODELS:
        raise ValueError(f"Modèle inconnu : {model}")
    if model not in _extractors:
        _extractors[model] = _EXTRACTOR_CLASSES[model]()
    return _extractors[model]
