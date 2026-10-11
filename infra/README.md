# Local infrastructure for the video streaming platform

## Services

- OpenMaxIO full management UI: http://localhost:9001
- MinIO S3 API: http://localhost:9000
- Valkey: localhost:6379
- Loki API: http://localhost:3100
- Grafana: http://localhost:3000

## Setup

The OpenMaxIO Console is built from source using the project linked below. Clone it into the build context first:

```bash
git clone --branch openMaxIO-main --depth 1 https://github.com/OpenMaxIO/openmaxio-object-browser.git openmaxio-object-browser
nvim .env
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs openmaxio-console-init
```

Change every example password, passphrase, and salt in `.env` before starting.

Open http://localhost:9001. Log in with `CONSOLE_ADMIN_USER` and `CONSOLE_ADMIN_PASSWORD` from `.env`. The one-shot initializer creates this MinIO user and attaches a broad admin policy for local development.

## Connection strings

- Compose apps: `http://minio:9000` for S3; `redis://valkey:6379/0` for Dramatiq/Redis-compatible clients.
- Host apps: `http://localhost:9000` for S3; `localhost:6379` for Valkey.

## Notes

- OpenMaxIO is a community-maintained fork of MinIO Console and is not affiliated with MinIO, Inc.: https://github.com/OpenMaxIO/openmaxio-object-browser
- This is a local-development configuration, not a production deployment.
- OpenMaxIO Console, Grafana, and Loki are published on loopback only. MinIO S3 and Valkey ports are published on the host interfaces; restrict them with your firewall if appropriate.
- The `consoleAdmin` policy grants broad administrative and S3 permissions. Do not expose the dashboard publicly with development credentials.
- Loki does not collect container logs automatically. Add Grafana Alloy or another log shipper when you want application/container logs sent to Loki.
- If the upstream OpenMaxIO build requirements change, update `Dockerfile.local` accordingly.
