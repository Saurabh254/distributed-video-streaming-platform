# Distributed Video Streaming Platform

A microservices-based distributed video streaming platform designed for educational and learning purposes. This project demonstrates video ingestion, catalog management, media playback, and observability across independent services.

> [!NOTE]
> This repository is created for educational and personal learning purposes.

---

## Architecture Overview

The platform is organized into independent microservices and shared infrastructure:

- **Web Application (`webapp/`)**: Modern Next.js frontend providing the user interface for browsing catalogs, uploading media, and streaming video.
- **Microservices (`services/`)**:
  - `auth_service`: Authentication and session management.
  - `catalog_service`: Metadata and video catalog indexation.
  - `playback_service`: Streaming sessions, segment delivery, and player coordination.
  - `video_service`: Video upload processing, ingestion, and transcoding pipeline.
- **Infrastructure (`infra/`)**:
  - **MinIO / OpenMaxIO**: S3-compatible distributed object storage for video blobs and HLS chunks.
  - **Valkey / Redis**: High-performance caching and task broker.
  - **Loki & Grafana**: Centralized log aggregation and system metrics monitoring.

---

## Tech Stack

- **Frontend**: Next.js, React, Tailwind CSS
- **Backend Services**: Python, FastAPI, uv
- **Data & Storage**: S3 / MinIO, Valkey / Redis
- **Observability**: Grafana, Loki
- **Containerization**: Docker Compose

---

## Getting Started

### 1. Infrastructure Setup

Navigate to the `infra` directory, configure environment variables, and start dependencies:

```bash
cd infra
cp .env.example .env
docker compose up -d --build
```

Access local endpoints:
- MinIO S3 Console: `http://localhost:9001`
- Grafana: `http://localhost:3000`

### 2. Services

Each service in `services/` is managed using [uv](https://docs.astral.sh/uv/):

```bash
cd services/<service_name>
uv run python -m <service_name>
```

### 3. Web Frontend

Run the Next.js development server:

```bash
cd webapp
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the client.

---

## License

Personal and educational project.
