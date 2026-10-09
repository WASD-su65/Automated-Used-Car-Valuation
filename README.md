# Automated Used Car Valuation using Multi-Feature Image Analysis and Machine Learning

[![CI](https://github.com/WASD-su65/Automated-Used-Car-Valuation/actions/workflows/ci.yml/badge.svg)](https://github.com/WASD-su65/Automated-Used-Car-Valuation/actions/workflows/ci.yml)

A full-stack web application (React, FastAPI, Docker) that wraps the project's deep learning models into a usable valuation tool.

Senior project, Department of Computer Science, Faculty of Science, Silpakorn University.
Registered: summer term, academic year 2568 (B.E.). Final defense: 18 October 2026.

A web application that estimates the price of a used car from photos. The user uploads four photos of the car (front, back, left, right) to identify the make, model and year, then uploads close-up photos of damaged areas to detect damage and adjust the estimated price.

## Features

- **Car identification** from four side photos using one EfficientNet-B4 model (11 supported classes). The model runs on each photo and the four probability vectors are averaged (multi-view averaging). The result also shows how many sides agree, with a warning when agreement is low.
- **Damage detection** using a YOLO model on up to four damage photos. Each photo has a zoom level (close, medium, wide) used to estimate damage size, and detections are grouped by type and severity.
- **Price estimation** that starts from a base price per car class and adjusts it for the detected damage.
- **React frontend** with image previews, loading and error states, and annotated result images.
- **Dockerized**: backend and frontend run together with Docker Compose.

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React (Vite), served by Nginx in production |
| Backend | FastAPI, Uvicorn |
| Models | TensorFlow / Keras (EfficientNet-B4), Ultralytics YOLO, OpenCV |
| Packaging | Docker, Docker Compose |

## Architecture

```
Browser (React, :3000)
        |  multipart/form-data
        v
FastAPI backend (:8000)
   |-- POST /identify-car    4 images -> EfficientNet-B4 x4 passes -> averaged probabilities
   |-- POST /assess-damage   up to 4 images -> YOLO -> damage list + annotated images + price
   '-- GET  /health
```

Models are loaded once when the server starts. Uploaded images are validated, written to temporary files, and removed after each request.

## Models are not included

The trained model files are not stored in this repository. Place these three files in `backend/models/` before running:

```
backend/models/best_efficientnet_model.keras
backend/models/damage_model.pt
backend/models/yolov8n.pt
```

The backend checks for these files at startup and stops with a clear message if any is missing. To request the trained models, contact the author.

## Run with Docker (recommended)

Requirements: Docker Desktop. Allocate at least 6 GB of memory to Docker, since TensorFlow and YOLO are loaded together.

```bash
docker compose up --build
```

- Web app: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs

Stop with `docker compose down`.

## Run without Docker (development)

Backend (Python 3.9):

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

The dev server runs at http://localhost:5173.

## API overview

| Endpoint | Input (multipart/form-data) | Output |
| --- | --- | --- |
| `POST /identify-car` | four images, one per side (front, back, left, right) | predicted class, confidence, number of agreeing sides, reliability flag, estimated base price |
| `POST /assess-damage` | up to four images with a `zoom_levels` and `sides` value for each, plus the car class | damage list, annotated images (base64), total estimated price |
| `GET /health` | none | service status |

See `http://localhost:8000/docs` for exact field names and example responses.

## Limitations

- The classifier only knows the 11 car classes it was trained on.
- Damage size is estimated from the selected zoom level, not measured against a full-body reference photo.
- The "reliable" flag (at least 3 of 4 sides agree) is a heuristic chosen for this project.
- HEIC images are not supported; use JPG or PNG.
- Prices are estimates for demonstration, not an official appraisal.

## Author

Poomipat Jitkrongsit