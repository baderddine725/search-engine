# Moteur de Recherche d'Images (TBIR + CBIR)

Moteur de recherche combinant la **recherche textuelle (TBIR)** et la **recherche par contenu visuel (CBIR)** utilisant Elasticsearch, InceptionV3, LBP, Flask et Streamlit, avec une comparaison complète face à VGG16.

## Architecture

```text
search-engine/
├── backend/
│   ├── app.py                  # API Flask
│   ├── config.py               # Configuration centralisée (registre des modèles)
│   ├── es_client.py            # Client Elasticsearch
│   ├── evaluation.py           # Métriques : précision@k, mAP, temps
│   ├── feature_extractor.py    # InceptionV3 + LBP, VGG16
│   ├── requirements.txt
│   └── Dockerfile
├── elasticsearch/
│   └── Dockerfile              # Elasticsearch 7.17.9 + plugin Elastiknn
├── frontend/
│   ├── app.py                  # Interface Streamlit multi-pages
│   ├── .streamlit/
│   │   └── config.toml
│   ├── requirements.txt
│   └── Dockerfile
├── scripts/
│   ├── extract_features.py     # Extraction des features des deux modèles
│   ├── index_text.py           # Indexation des métadonnées Flickr
│   ├── index_images.py         # Indexation des vecteurs images
│   └── evaluate.py             # Évaluation comparative
├── data/
│   ├── bdimage/                # Images classées par dossier
│   ├── photo_metadata.csv      # Métadonnées Flickr
│   ├── features.csv            # Features InceptionV3 + LBP (généré)
│   ├── features_vgg16.csv      # Features VGG16 (généré)
│   ├── extraction_stats.json   # Statistiques d'extraction (généré)
│   └── benchmark.json          # Rapport d'évaluation (généré)
├── docker-compose.yml
└── README.md
```

## Prérequis

- Docker et Docker Compose
- Au moins 6 Go de RAM alloués à Docker pour Elasticsearch et TensorFlow avec les deux modèles
- Python et les dépendances définies dans les fichiers `requirements.txt` pour une exécution hors Docker

## Données

### 1. Métadonnées Flickr

Placer le fichier `photo_metadata.csv` dans le dossier `data/`.

Les colonnes attendues sont :

- `photo_id`
- `title`
- `tags`
- `description`
- `farm`
- `server`
- `secret`

### 2. Base d'images Bdimage

Placer les images dans `data/bdimage/`, organisées par classe. Le nom du dossier sert de vérité terrain pour l'évaluation.

Exemple :

```text
data/bdimage/
├── avion/
├── chat/
├── voiture/
└── ...
```

Chaque dossier contient les images correspondant à une classe.

## Installation et lancement

### 1. Démarrer les services

Depuis la racine du projet, exécuter :

```bash
docker compose up -d --build
```

Le plugin Elastiknn est configuré dans l'image Elasticsearch. Selon la configuration du Dockerfile, les poids ImageNet peuvent être téléchargés lors de la construction ou au premier chargement du modèle.

Vérifier l'état des conteneurs :

```bash
docker compose ps
```

Consulter les journaux en cas de problème :

```bash
docker compose logs -f
```

### 2. Indexer les données

Exécuter les commandes suivantes après le démarrage des services et la disponibilité d'Elasticsearch.

#### Indexation des métadonnées textuelles

```bash
docker exec backend-search-engine python /scripts/index_text.py
```

#### Extraction des caractéristiques visuelles

```bash
docker exec backend-search-engine python /scripts/extract_features.py
```

Cette étape extrait les caractéristiques visuelles pour les deux modèles, InceptionV3 + LBP et VGG16, selon l'implémentation du script.

#### Indexation des vecteurs d'images

```bash
docker exec backend-search-engine python /scripts/index_images.py
```

Les vecteurs sont indexés dans Elasticsearch, notamment dans les index `images_data` et `images_vgg16`, selon la configuration du projet.

#### Évaluation comparative

```bash
docker exec backend-search-engine python /scripts/evaluate.py
```

Le rapport d'évaluation est enregistré dans `data/benchmark.json`, selon la configuration du script.

### 3. Exécuter un seul modèle

Si les scripts prennent en charge l'option `--model`, il est possible de sélectionner un modèle :

```bash
docker exec backend-search-engine python /scripts/extract_features.py --model inception_lbp
```

```bash
docker exec backend-search-engine python /scripts/extract_features.py --model vgg16
```

La disponibilité de cette option dépend de l'implémentation effective de chaque script.

### 4. Particularité de Git Bash sous Windows

Dans Git Bash, les chemins commençant par `/scripts/` peuvent être convertis automatiquement en chemins Windows.

Pour éviter cette conversion, préfixer les commandes concernées avec :

```bash
MSYS_NO_PATHCONV=1
```

Exemple :

```bash
MSYS_NO_PATHCONV=1 docker exec backend-search-engine python /scripts/index_text.py
```

## Utilisation

Une fois les services démarrés, les interfaces sont accessibles localement.

### Frontend Streamlit

URL : [http://localhost:8501](http://localhost:8501)

Fonctionnalités :

- **Accueil** : état des services, volumétrie et répartition des classes.
- **Recherche textuelle** : recherche multi-champs, tolérance aux fautes et mise en évidence des termes.
- **Recherche par image** : recherche à partir d'une image de la base, d'une image téléversée ou d'une URL, avec sélection du modèle.
- **Images similaires** : lancement d'une recherche à partir d'une image retournée.
- **Comparaison des modèles** : comparaison des résultats d'InceptionV3 + LBP et de VGG16 pour une même requête.
- **Évaluation globale** : précision@k, mAP, P@1, courbe précision/rang, résultats par classe et temps d'exécution, selon les métriques implémentées.

### API Flask

URL : [http://localhost:5000](http://localhost:5000)

L'API expose les fonctionnalités de recherche, de comparaison et d'évaluation décrites ci-dessous.

## Comparaison InceptionV3 + LBP vs VGG16

Le projet compare deux approches de représentation visuelle.

| Caractéristique | InceptionV3 + LBP | VGG16 |
|---|---|---|
| Rôle | Approche proposée | Modèle de référence |
| Taille d'entrée | 299 × 299 pixels | 224 × 224 pixels |
| Descripteur CNN | 2 048 dimensions | 512 dimensions |
| Descripteur de texture | Histogramme LBP de 10 bins | Aucun dans cette configuration |
| Représentation finale | CNN + texture LBP | CNN |
| Index Elasticsearch | `images_data` | `images_vgg16` |
| Recherche approximative | LSH, avec `w = 3` dans la configuration initiale | LSH, avec `w = 15` dans la configuration initiale |

Les valeurs de configuration doivent être vérifiées dans le code avant de considérer ce tableau comme une description définitive de l'implémentation.

### Protocole d'évaluation

Le protocole consiste à utiliser chaque image indexée comme requête, en excluant cette image de ses propres résultats.

Un résultat est considéré comme pertinent lorsqu'il appartient à la même classe que l'image requête. La classe est déterminée à partir de l'organisation des dossiers de la base d'images.

Les deux modèles sont évalués sur les mêmes requêtes, avec deux modes de recherche :

1. **Recherche approximative** : utilisation de l'index LSH réellement configuré dans Elasticsearch.
2. **Recherche exacte** : comparaison des descripteurs sans approximation LSH, si cette fonctionnalité est prise en charge par l'implémentation.

Les métriques peuvent inclure :

- **Précision@k** : proportion de résultats pertinents parmi les `k` premiers résultats.
- **mAP (mean Average Precision)** : moyenne de la précision moyenne sur l'ensemble des requêtes.
- **P@1** : pertinence du premier résultat retourné.
- **Temps d'extraction** : temps nécessaire pour calculer les descripteurs.
- **Temps de recherche** : temps nécessaire pour récupérer les résultats.
- **Résultats par classe** : analyse des performances selon la catégorie d'image.

### Normalisation et paramètres LSH

Les vecteurs issus de VGG16 peuvent avoir une échelle numérique différente de celle des vecteurs issus d'InceptionV3 + LBP.

Le paramètre `w` du mécanisme LSH doit donc être configuré avec précaution. Une comparaison équitable exige également de contrôler la normalisation des vecteurs, le nombre de résultats retournés, les images utilisées et les paramètres de recherche.

Les valeurs `w = 3` et `w = 15` correspondent à la configuration initiale du projet et ne constituent pas des valeurs universellement optimales.

## Endpoints API

Les routes suivantes correspondent aux endpoints documentés du projet. Les méthodes et paramètres exacts doivent être confirmés dans `backend/app.py`.

| Méthode | Route | Description |
|---|---|---|
| GET | `/health` | Vérification de l'état du service |
| GET | `/models` | Liste des modèles CBIR disponibles |
| GET | `/stats` | Statistiques des index et des classes |
| GET | `/search/text` | Recherche textuelle avec `q` et `size` |
| POST | `/search/image` | Recherche par image téléversée |
| POST | `/search/url` | Recherche à partir d'une URL d'image |
| GET | `/search/similar` | Recherche à partir d'une image de la base |
| POST | `/compare` | Comparaison entre les modèles |
| GET | `/benchmark` | Récupération du dernier rapport d'évaluation |
| POST | `/benchmark/run` | Lancement d'une nouvelle évaluation |
| GET | `/dataset/images` | Liste des images indexées |
| GET | `/images/<path>` | Accès à une image de la base |
| POST | `/init` | Initialisation des index Elasticsearch |

### Paramètres principaux

- Recherche textuelle : `q`, `size`
- Recherche par image : `image`, `size`, `model`
- Recherche par URL : `url`, `size`, `model`
- Images similaires : `path`, `size`, `model`
- Comparaison : `path`, `image` ou `url`, `size`, `query_class`
- Évaluation : `k`, `per_class`, `candidates`

Les paramètres disponibles et leurs valeurs par défaut dépendent de l'implémentation de l'API.

## Exemples d'utilisation de l'API

### 1. Recherche textuelle

```bash
curl "http://localhost:5000/search/text?q=sunset+beach&size=5"
```

### 2. Recherche par image avec VGG16

```bash
curl -X POST "http://localhost:5000/search/image" \
  -F "image=@photo.jpg" \
  -F "size=10" \
  -F "model=vgg16"
```

### 3. Comparaison des modèles à partir d'une image de la base

```bash
curl -X POST "http://localhost:5000/compare" \
  -d "path=roses/123.jpg" \
  -d "size=10"
```

### 4. Comparaison à partir d'une URL

```bash
curl -X POST "http://localhost:5000/compare" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/photo.jpg","size":10,"query_class":"roses"}'
```

Ces exemples supposent que les noms de routes et les paramètres correspondent à l'implémentation actuelle.

## Technologies utilisées

- **Elasticsearch 7.17.9** : moteur d'indexation et de recherche.
- **Elastiknn 7.17.9.0** : recherche vectorielle approximative, selon les fonctionnalités activées.
- **InceptionV3** : extraction de caractéristiques visuelles avec TensorFlow/Keras.
- **LBP (Local Binary Patterns)** : description de la texture des images.
- **VGG16** : modèle de référence pour la comparaison des descripteurs CNN.
- **Flask** : développement de l'API REST backend.
- **Streamlit** : interface utilisateur interactive et multi-pages.
- **Altair** : visualisation des résultats et des métriques.
- **Docker et Docker Compose** : conteneurisation et orchestration des services.
- **Python** : implémentation de la logique de recherche, d'extraction et d'évaluation.

## Structure des résultats générés

Selon les scripts et les chemins configurés, le projet peut générer :

| Fichier | Contenu |
|---|---|
| `data/features.csv` | Descripteurs InceptionV3 + LBP |
| `data/features_vgg16.csv` | Descripteurs VGG16 |
| `data/extraction_stats.json` | Statistiques d'extraction |
| `data/benchmark.json` | Résultats de l'évaluation comparative |

Ces fichiers sont générés par les scripts du projet et ne doivent pas nécessairement être versionnés sur GitHub, notamment s'ils sont volumineux.

## Dépannage

### Elasticsearch ne démarre pas

Vérifier les journaux :

```bash
docker compose logs elasticsearch
```

Vérifier également la mémoire disponible et la configuration du service dans `docker-compose.yml`.

### Les conteneurs ne sont pas prêts

Afficher leur état :

```bash
docker compose ps
```

Puis consulter les journaux :

```bash
docker compose logs -f
```

### L'indexation échoue

Vérifier que :

- Elasticsearch est accessible.
- Le fichier `photo_metadata.csv` se trouve dans le dossier attendu.
- Les images sont présentes dans `data/bdimage/`.
- Les chemins utilisés dans les conteneurs correspondent aux volumes Docker configurés.
- Les dépendances Python sont installées.

### Les résultats de recherche sont vides

Vérifier que les index ont été créés et alimentés, puis contrôler les noms d'index utilisés dans la configuration.

## Licence et utilisation

Ajouter ici la licence du projet si celui-ci est distribué publiquement. En l'absence de licence explicite, les conditions de réutilisation du code ne doivent pas être considérées comme automatiquement autorisées.

---

**Projet :** Moteur de recherche d'images combinant recherche textuelle et recherche visuelle.

**Objectif :** Comparer les performances d'une représentation InceptionV3 enrichie par LBP avec celles de VGG16, au sein d'une architecture basée sur Elasticsearch, Flask, Streamlit et Docker.
- **Elasticsearch 7.17.9** + plugin Elastiknn 7.17.9.0 (L2 LSH et recherche exacte)
- **InceptionV3** (TensorFlow/Keras) — vecteur CNN 2048 dims
- **LBP** (scikit-image) — histogramme texture 10 bins
- **VGG16** (TensorFlow/Keras) — vecteur CNN 512 dims (référence)
- **Flask** — API REST backend
- **Streamlit** + Altair — interface utilisateur et graphiques
- **Docker Compose** — orchestration
# search-engine

## MIRFLICKR-1M (optionnel)

Pour activer la base d'un million d'images Flickr avec les descripteurs MPEG-7
fournis (Edge Histogram et Homogeneous Texture) :

```bash
# 1) Télécharger les archives dans data/mirflickr/
#    (depuis http://press.liacs.nl/mirflickr/mirflickr1m.v3b/)
#      tags.zip, license.zip,
#      features_edgehistogram.zip, features_homogeneoustexture.zip

# 2) Indexation complète (texte dans ES + MPEG-7 en memmap + VP-Tree)
docker exec backend-search-engine python /scripts/index_mirflickr.py
```

Le script crée l'index Elasticsearch `mirflickr` (1 M documents : title, tags,
owner, licence, URL), deux fichiers `data/mirflickr/{edge,homo}.npy`
(float32 memmap, chargés sans copier en RAM), et deux `*_vptree.npz`
partitionnant l'espace L1 pour la recherche k-NN rapide
(élagage ≈ 96 % → **~50 ms** par requête sur 1 M points, vs ~3 s en scan linéaire).

Routes dédiées :

| Route                         | Rôle                                                  |
|-------------------------------|-------------------------------------------------------|
| `GET  /mirflickr/stats`       | État des index et descripteurs disponibles            |
| `GET  /mirflickr/search?q=`   | Recherche textuelle BM25 (1 M documents)              |
| `GET  /mirflickr/similar`     | k-NN MPEG-7 (`?photo_id=…&descriptor=edge\|homo`)     |
