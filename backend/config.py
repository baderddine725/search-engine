"""Configuration du moteur de recherche."""

import os

# Elasticsearch
ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = int(os.getenv("ES_PORT", 9200))
ES_URL = f"http://{ES_HOST}:{ES_PORT}"

# Index names
TEXT_INDEX = "flickrphotos"
IMAGE_INDEX = "images_data"          # InceptionV3 + LBP (notre approche)
VGG16_INDEX = "images_vgg16"         # VGG16 (approche de référence)

# Feature extraction
CNN_DIMS = 2048       # InceptionV3 output
LBP_BINS = 10         # LBP histogram bins
TOTAL_DIMS = CNN_DIMS + LBP_BINS  # 2058
VGG16_DIMS = 512      # VGG16 (global average pooling sur block5)

# ANN search
ANN_CANDIDATES = 50
DEFAULT_RESULTS = 10

# LBP parameters
LBP_RADIUS = 1
LBP_N_POINTS = 8

# Image preprocessing
IMG_SIZE = (299, 299)        # InceptionV3 input size
VGG16_IMG_SIZE = (224, 224)  # VGG16 input size

# Paths
DATA_DIR = os.getenv("DATA_DIR", "/app/data")
BDIMAGE_DIR = os.path.join(DATA_DIR, "bdimage")
CSV_PATH = os.path.join(DATA_DIR, "photo_metadata.csv")
FEATURES_CSV = os.path.join(DATA_DIR, "features.csv")
VGG16_FEATURES_CSV = os.path.join(DATA_DIR, "features_vgg16.csv")
BENCHMARK_JSON = os.path.join(DATA_DIR, "benchmark.json")
EXTRACTION_STATS_JSON = os.path.join(DATA_DIR, "extraction_stats.json")

# Modèles de recherche par contenu comparés
DEFAULT_MODEL = "inception_lbp"
MODELS = {
    "inception_lbp": {
        "label": "InceptionV3 + LBP",
        "description": "Notre approche : CNN InceptionV3 (2048) + histogramme LBP (10)",
        "index": IMAGE_INDEX,
        "dims": TOTAL_DIMS,
        "features_csv": FEATURES_CSV,
    },
    "vgg16": {
        "label": "VGG16",
        "description": "Référence : CNN VGG16 pré-entraîné ImageNet (512)",
        "index": VGG16_INDEX,
        "dims": VGG16_DIMS,
        "features_csv": VGG16_FEATURES_CSV,
        # Les vecteurs VGG16 ont une norme ~5x plus grande (≈103 vs ≈20) :
        # w est mis à l'échelle pour garder le même rapport largeur de seau / distance.
        "lsh": {"L": 99, "k": 1, "w": 15},
    },
}

# Upload
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"}
