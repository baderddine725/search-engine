FROM python:3.10-slim

WORKDIR /app

# Dépendances système pour OpenCV et scikit-image
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Poids ImageNet téléchargés à la construction (pas au démarrage des workers)
RUN python -c "from tensorflow.keras.applications import InceptionV3, VGG16; \
InceptionV3(weights='imagenet', include_top=False); VGG16(weights='imagenet', include_top=False)"

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "600", "--workers", "2", "app:app"]
