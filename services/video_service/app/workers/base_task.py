from celery import Task

from app.workers.publisher import publish_event


class BaseTask(Task):
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True
    max_retries = 5

    abstract = True

    def before_start(self, task_id, args, kwargs):
        publish_event(
            event="task.started",
            task_id=task_id,
            task_name=self.name,
            args=args,
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        publish_event(
            event="task.retrying",
            task_id=task_id,
            task_name=self.name,
            error=repr(exc),
            retry_count=self.request.retries,
        )

    def on_success(self, retval, task_id, args, kwargs):
        publish_event(
            event="task.succeeded",
            task_id=task_id,
            task_name=self.name,
        )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        publish_event(
            event="task.failed",
            task_id=task_id,
            task_name=self.name,
            error=repr(exc),
        )

        self.app.send_task(
            "app.workers.tasks.dead_letter.record_dead_letter",
            kwargs={
                "original_task": self.name,
                "task_id": task_id,
                "args": args,
                "kwargs": kwargs,
                "error": repr(exc),
                "traceback": str(einfo) if einfo else None,
            },
            queue="video.dlq",
        )
