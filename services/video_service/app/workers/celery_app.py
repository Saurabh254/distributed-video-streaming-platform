from celery import Celery
from kombu.entity import Queue

app = Celery(
    "video-worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)
app.conf.imports = ("app.workers.tasks.video", "app.workers.tasks.dead_letter")
app.conf.update(
    task_queues=(
        Queue("video-processing"),
        Queue("video.dlq"),
    ),
    task_default_queue="video-processing",
)
