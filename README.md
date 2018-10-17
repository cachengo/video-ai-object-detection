# video-ai-object-detection
A sample service that performs object detection with horizontal clustering capabilities

CONTAINER_ROLE= server|inference|[all]
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
FRAMES_PER_CHUNK = os.environ.get('FRAMES_PER_CHUNK', 100)
LEADER_NODE_URL = os.environ.get('LEADER_NODE_URL', 'http://localhost:5000/videos/')
INFERENCE_MODEL = os.environ.get('INFERENCE_MODEL', 'ssdlite_mobilenet_v2_coco_2018_05_09')