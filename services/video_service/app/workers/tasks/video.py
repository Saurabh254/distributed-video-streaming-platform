from app.workers.base_task import BaseTask
from app.workers.celery_app import app


class VideoTask(BaseTask):
    abstract = True


@app.task(bind=True, base=VideoTask, queue="video-processing")
def process_video(self, video_id: str):
    print(f"Processing video: {video_id}")
    raise Exception("life is full of exception")
    return {"video_id": video_id, "status": "completed"}
