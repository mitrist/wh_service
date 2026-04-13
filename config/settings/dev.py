from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)  # noqa: F405
