# Distributed Video Streaming Platform

A microservices-based distributed video streaming platform designed for educational and learning purposes. This project demonstrates direct-to-storage video ingestion, asynchronous media processing pipelines (Dramatiq + Redis Streams), multi-bitrate HLS adaptive streaming, catalog management, and observability across independent services.

> [!NOTE]
> This repository is created for educational and personal learning purposes.

---

## Architecture Overview

The platform employs a decoupled microservices architecture with direct-to-object-storage uploads, event-driven background processing, and adaptive bitrate delivery:

```mermaid
flowchart TD
    subgraph Client ["Client Layer"]
        Browser["Web Browser (Next.js Client)"]
    end

    subgraph Gateway ["Edge & API Gateway"]
        NextGateway["Next.js API Gateway (/api/*)"]
    end

    subgraph Services ["Backend Microservices"]
        AuthSvc["auth_service (FastAPI :8000)<br/>JWT, HttpOnly Cookies, Sessions"]
        VideoSvc["video_service (FastAPI :8001)<br/>Uploads, Metadata, Lifecycle"]
        CatalogSvc["catalog_service (FastAPI :8002)<br/>Discovery, Search, Caching"]
        PlaybackSvc["playback_service (FastAPI :8003)<br/>HLS Session Token, Telemetry, Views"]
    end

    subgraph DataPlane ["Storage & Data Plane"]
        PostgresAuth[("PostgreSQL: auth_db")]
        PostgresVideo[("PostgreSQL: video_db")]
        MinIORaw[("MinIO: raw-videos")]
        MinIOProcessed[("MinIO: processed-videos")]
        RedisStreams[("Redis Streams<br/>stream:video:events")]
        RedisBroker[("Redis Dramatiq Broker<br/>dramatiq:default")]
    end

    subgraph ProcessingPlane ["Asynchronous Media Pipeline"]
        Dispatcher["Redis Stream Dispatcher<br/>(Consumer Group: cg:video_service)"]
        DramatiqWorkers["Dramatiq Processing Workers"]
        FFmpegThumbnail["Thumbnail Processor<br/>(FFmpeg + Pillow)"]
        FFmpegHLS["HLS ABR Transcoder<br/>(FFmpeg Multi-Variant Ladder)"]
    end

    %% Client Interactions
    Browser -->|"1. Auth / Video Metadata Requests"| NextGateway
    Browser -->|"3. Direct S3 Upload (Presigned PUT)"| MinIORaw
    Browser -->|"Play HLS Stream"| MinIOProcessed

    %% Gateway Routing
    NextGateway -->|"/api/auth/*"| AuthSvc
    NextGateway -->|"/api/videos/*"| VideoSvc
    NextGateway -->|"/api/catalog/*"| CatalogSvc
    NextGateway -->|"/api/playback/*"| PlaybackSvc

    %% Service Data Connections
    AuthSvc --> PostgresAuth
    VideoSvc --> PostgresVideo
    VideoSvc -->|"Generate Presigned PUT / HeadObject"| MinIORaw
    VideoSvc -->|"XADD video_uploaded"| RedisStreams

    %% Background Processing Pipeline
    Dispatcher -->|"XREADGROUP consumer"| RedisStreams
    Dispatcher -->|"Enqueue Actors"| RedisBroker
    RedisBroker --> DramatiqWorkers
    DramatiqWorkers --> FFmpegThumbnail
    DramatiqWorkers --> FFmpegHLS
    FFmpegThumbnail -->|"Extract Keyframe & Upload WebP/JPG"| MinIOProcessed
    FFmpegThumbnail -->|"Update thumbnail_url"| PostgresVideo
    FFmpegHLS -->|"Transcode 1080p/720p/480p/360p & Upload"| MinIOProcessed
    FFmpegHLS -->|"Update master.m3u8 & status=READY"| PostgresVideo
```

---

## End-to-End Video Ingestion & Processing Flow

The platform decouples high-bandwidth media ingestion from service instances by utilizing **S3 Presigned PUT URLs**, event streaming with **Redis Streams**, and distributed task queues via **Dramatiq**:

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Browser
    participant Gateway as Next.js API Gateway
    participant VideoSvc as Video Service (:8002)
    participant MinIO as MinIO S3 Storage
    participant DB as PostgreSQL (video_db)
    participant Redis as Redis Streams & Broker
    participant Dispatcher as Stream Dispatcher
    participant Worker as Dramatiq Worker (FFmpeg)

    %% Phase 1: Upload Initiation
    Note over User, MinIO: Phase 1: Presigned Direct Upload
    User->>Gateway: POST /api/videos/upload-url (title, filename, content_type)
    Gateway->>VideoSvc: POST /api/v1/videos/upload-url [Bearer JWT]
    VideoSvc->>DB: INSERT INTO videos (status='PENDING')
    VideoSvc->>MinIO: Generate Presigned PUT URL (raw-videos/...)
    MinIO-->>VideoSvc: Presigned Upload URL
    VideoSvc-->>Gateway: { video_id, upload_url, s3_key }
    Gateway-->>User: { video_id, upload_url, s3_key }

    %% Direct S3 Upload
    User->>MinIO: HTTP PUT raw video file (Direct binary stream with progress)
    MinIO-->>User: 200 OK (Upload complete)

    %% Phase 2: Completion & Event Trigger
    Note over User, Redis: Phase 2: Upload Verification & Event Notification
    User->>Gateway: POST /api/videos/{id}/complete
    Gateway->>VideoSvc: POST /api/v1/videos/{id}/complete [Bearer JWT]
    VideoSvc->>MinIO: HEAD object (Verify file existence & size)
    MinIO-->>VideoSvc: 200 OK (Object verified)
    VideoSvc->>DB: UPDATE videos SET status='UPLOADED', file_size=bytes
    VideoSvc->>Redis: XADD stream:video:events { event: "video_uploaded", video_id }
    VideoSvc-->>Gateway: { status: "UPLOADED", message: "Processing started" }
    Gateway-->>User: 200 OK

    %% Phase 3: Background Asynchronous Processing
    Note over Redis, Worker: Phase 3: Distributed Media Processing Pipeline
    Dispatcher->>Redis: XREADGROUP GROUP cg:video_service
    Redis-->>Dispatcher: Message: video_uploaded (video_id)
    Dispatcher->>Redis: Enqueue Dramatiq actors: process_video_thumbnail & transcode_video_hls
    Dispatcher->>Redis: XACK stream:video:events cg:video_service msg_id

    par Thumbnail Processing Actor
        Worker->>DB: UPDATE videos SET thumbnail_status='PROCESSING'
        Worker->>MinIO: Download raw video (temp sandbox)
        Worker->>Worker: FFmpeg extract keyframe at 1.0s + Pillow resize (WebP/JPEG)
        Worker->>MinIO: Upload thumbnails (original, medium 640x360, small 320x180) to processed-videos
        Worker->>DB: UPDATE videos SET thumbnail_url=..., thumbnail_status='READY'
    and Multi-Variant HLS Transcoding Actor
        Worker->>DB: UPDATE videos SET hls_status='PROCESSING'
        Worker->>MinIO: Download raw video (temp sandbox)
        Worker->>Worker: Probe duration, width, height (ffprobe)
        Worker->>Worker: FFmpeg multi-bitrate ABR transcode (1080p, 720p, 480p, 360p)
        Worker->>Worker: Generate master.m3u8 with relative variant playlist paths
        Worker->>MinIO: Upload master.m3u8, variant playlists, and .ts segments to processed-videos
        Worker->>DB: UPDATE videos SET hls_master_playlist_url=..., hls_status='READY', status='READY'
    end
```

---

## HLS Transcoding & Media Specifications

The video processing pipeline automatically generates an **Adaptive Bitrate (ABR)** ladder using FFmpeg and segments media into HLS format:

| Variant | Resolution | Video Bitrate | Audio Bitrate | Target Frame Rate |
| :--- | :--- | :--- | :--- | :--- |
| **1080p (Full HD)** | 1920 &times; 1080 | 5000 kbps | 192 kbps | 30 fps |
| **720p (HD)** | 1280 &times; 720 | 2800 kbps | 128 kbps | 30 fps |
| **480p (SD)** | 854 &times; 480 | 1400 kbps | 128 kbps | 30 fps |
| **360p (Low)** | 640 &times; 360 | 800 kbps | 96 kbps | 30 fps |

- **Segment Duration**: 6 seconds per segment (`.ts`).
- **Master Playlist (`master.m3u8`)**: Uses relative paths (`1080p/index.m3u8`, `720p/index.m3u8`), ensuring portability across S3 buckets and CDNs without hardcoded domain dependencies.
- **Thumbnails**: Multi-resolution image bundle (`original.webp`, `medium.webp`, `small.webp`, and `.jpg` fallbacks) generated via FFmpeg keyframe capture and Pillow Lanczos resampling.

---

## Repository Structure

```text
distributed-video-streaming-platform/
├── infra/                      # Docker Compose & local infrastructure configs
│   ├── docker-compose.yml      # MinIO, PostgreSQL, Valkey/Redis, Loki, Grafana
│   └── .env.example
├── services/
│   ├── auth_service/           # FastAPI Authentication & User Management
│   │   ├── app/                # JWT tokens, HttpOnly cookies, session management
│   │   └── tests/              # 20 unit and integration tests
│   ├── video_service/          # FastAPI Video Ingestion & Processing Pipeline
│   │   ├── app/
│   │   │   ├── api/            # Presigned URL generation & completion endpoints
│   │   │   ├── core/           # S3, Redis, PostgreSQL connectors & config
│   │   │   ├── repository/     # Asynchronous database queries
│   │   │   ├── services/       # Video upload business logic & S3 verification
│   │   │   └── workers/        # Dramatiq actors, Redis stream dispatcher, FFmpeg
│   │   └── tests/              # 13 unit and pipeline integration tests
│   ├── catalog_service/        # FastAPI Video Catalog & Discovery Service (:8002)
│   │   ├── app/                # Catalog queries, search, and Redis caching
│   │   └── tests/              # 7 unit and integration tests
│   └── playback_service/       # FastAPI Playback Session & Streaming Service (:8003)
│       ├── app/                # HLS manifest resolution, heartbeat, and view counters
│       └── tests/              # 8 unit and integration tests
└── webapp/                     # Next.js 16 (React 19, Tailwind CSS)
    ├── app/
    │   ├── api/auth/           # API Gateway routes for authentication
    │   └── api/videos/         # API Gateway routes for presigned uploads & status
    ├── components/
    │   ├── AuthModal.tsx       # Sign in / Sign up interactive modal
    │   ├── Navbar.tsx          # Navigation, search bar, user menu, and upload CTA
    │   └── UploadModal.tsx     # Drag-and-drop video upload with XHR progress
    └── lib/                    # Client APIs, auth context, and server helpers
```

---

## Tech Stack

- **Frontend & Gateway**: Next.js 16 (App Router), React 19, Tailwind CSS, Lucide Icons
- **Backend Microservices**: Python 3.12, FastAPI, Asyncpg, Pydantic v2, uv
- **Media Engine**: FFmpeg, FFprobe, Pillow (PIL)
- **Task Queue & Event Bus**: Dramatiq, Redis Streams, Valkey / Redis
- **Storage & Databases**: MinIO (S3-compatible distributed object store), PostgreSQL
- **Observability**: Grafana, Loki, Promtail
- **Tooling**: Docker Compose, Ruff, Pytest, Pytest-Asyncio

---

## Getting Started

### 1. Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [uv](https://docs.astral.sh/uv/) (Fast Python package manager)
- [Node.js](https://nodejs.org/) (v18+) & [pnpm](https://pnpm.io/)
- [FFmpeg](https://ffmpeg.org/) (installed locally for worker processes)

### 2. Infrastructure Setup

Start MinIO, PostgreSQL, and Valkey/Redis:

```bash
cd infra
cp .env.example .env
docker compose up -d
```

Endpoints:
- **MinIO Console**: [http://localhost:9001](http://localhost:9001) (Credentials: `minioadmin` / `minioadmin`)
- **MinIO S3 API**: [http://localhost:9000](http://localhost:9000)
- **Grafana**: [http://localhost:3000](http://localhost:3000)
- **Redis / Valkey**: `localhost:6379`
- **PostgreSQL**: `localhost:5432`

### 3. Running Services

#### Video Service

```bash
cd services/video_service
cp .env.example .env
uv sync

# Terminal 1: Run the FastAPI Web Server (Port 8002)
make run

# Terminal 2: Run the Dramatiq Media Workers (FFmpeg)
make worker

# Terminal 3: Run the Redis Stream Dispatcher
make dispatcher
```

To run the video service tests:
```bash
make test
```

#### Auth Service

```bash
cd services/auth_service
cp .env.example .env
uv sync

# Run the FastAPI Auth Server (Port 8001)
make run

#### Catalog Service

```bash
cd services/catalog_service
cp .env.example .env
uv sync

# Run the FastAPI Catalog Server (Port 8002)
make run

# Run tests
make test
```

#### Playback Service

```bash
cd services/playback_service
cp .env.example .env
uv sync

# Run the FastAPI Playback Server (Port 8003)
make run

# Run tests
make test
```

### 4. Running the Web Frontend

```bash
cd webapp
pnpm install
pnpm dev
```

Open [http://localhost:4000](http://localhost:4000) to access the application.

---

## Observability & Monitoring (Grafana + Loki)

The platform includes a production-grade observability stack featuring auto-provisioned Grafana dashboards, log aggregation with Loki, and real-time log shipping via Promtail.

### Infrastructure Access

| Component | Endpoint | Credentials | Purpose |
| :--- | :--- | :--- | :--- |
| **Grafana** | [http://localhost:3000](http://localhost:3000) | `admin` / `12345678` | Metrics, logs, worker queues, and playback telemetry |
| **Loki** | [http://localhost:3100](http://localhost:3100) | None (Internal) | Centralized structured log store and LogQL engine |
| **Promtail** | [http://localhost:9080](http://localhost:9080) | None (Internal) | Agent streaming `/infra/logs/*.log` to Loki |
| **MinIO Console** | [http://localhost:9001](http://localhost:9001) | `localminio` / `12345678` | S3 Buckets management |

### Provisioned Dashboards

All dashboards are pre-configured in `infra/grafana/dashboards/` and auto-loaded on container startup:

1. **AuraStream - Platform Overview** (`/d/aurastream-platform-overview`)
   - High-level platform KPIs: Registered users, videos ingested, HLS ready count, total platform views.
   - Live cross-service request rate (req/s), error distribution, and log level breakdown.
   - Unified cross-service live log stream.

2. **AuraStream - Microservices Logs & Traces** (`/d/aurastream-microservices-logs`)
   - Interactive log analysis with dropdown filters for `service` (`auth-service`, `video-service`, `catalog-service`, `playback-service`, `video-worker`, `video-dispatcher`).
   - Log level filtering (`INFO`, `WARN`, `ERROR`, `DEBUG`) and keyword search.
   - Real-time LogQL stream with parsed JSON metadata.

3. **AuraStream - Video Processing Pipeline & Workers** (`/d/aurastream-pipeline-workers`)
   - Media pipeline tracking: Active transcoding jobs, completed HLS videos, failed processing counts.
   - Redis Stream event throughput and Dramatiq worker execution rates.
   - Video processing registry table (video titles, resolutions, durations, HLS status).
   - Dedicated Dramatiq & Dispatcher worker log stream.

4. **AuraStream - Video Streaming & Telemetry** (`/d/aurastream-streaming-telemetry`)
   - Video engagement analytics: Total plays, watch progress %, completed sessions, active viewers (last 15m).
   - Top catalog videos ranked by views and likes.
   - Recent playback heartbeat sessions with real-time watch percentage progress gauges.
   - Dedicated playback service log stream.

---

## License

Personal and educational project.

