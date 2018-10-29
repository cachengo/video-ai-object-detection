import hashlib
import os
import uuid

import six.moves.urllib as urllib
import skvideo.io
from celery import Celery
from celery.utils.log import get_task_logger
from celery.signals import worker_init, worker_process_init
from celery.concurrency import asynpool

from object_detector import ObjectDetector


asynpool.PROC_ALIVE_TIMEOUT = 100.0  # set this long enough

LOGGER = get_task_logger(__name__)

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
FRAMES_PER_CHUNK = os.environ.get('FRAMES_PER_CHUNK', 100)
LEADER_NODE_URL = os.environ.get('LEADER_NODE_URL', 'http://localhost:5000/videos/')
INFERENCE_MODEL = os.environ.get('INFERENCE_MODEL', 'ssdlite_mobilenet_v2_coco_2018_05_09')


# Celery: Distributed Task Queue
WORKER = Celery('tasks', backend=CELERY_RESULT_BACKEND, broker=CELERY_BROKER_URL)
WORKER.conf.task_serializer = 'json'
WORKER.conf.result_serializer = 'json'
WORKER.conf.task_routes = {
    'split_video': {'queue': 'server'},
    'infer_from_video': {'queue': 'inference'}
}

DETECTOR = None


def store_frame_metadata(video_name, frame_number, metadata, start_frame=0):
    pass

@worker_process_init.connect()
def on_worker_init(**_):
    global DETECTOR
    DETECTOR = ObjectDetector(INFERENCE_MODEL)
    LOGGER.info('Worker initialized with model')


@WORKER.task(name='infer_from_video')
def infer_from_video(chunk_name, parent_name, chunk_start_frame):
    LOGGER.info('Started processing video')
    image_path = '/images/{}'
    opener = urllib.request.URLopener()
    chunk_path = image_path.format(chunk_name)
    opener.retrieve(LEADER_NODE_URL + chunk_name, chunk_path)
    output_fn = lambda frame, meta: store_frame_metadata(
        parent_name, frame, meta, chunk_start_frame)
    DETECTOR.run_inference_for_video(chunk_path, output_fn=output_fn)
    LOGGER.info('Finished processing video')


@WORKER.task(name='split_video')
def split_video(video_url):
    filename = '{}.mp4'.format(hashlib.md5(video_url.encode()).hexdigest())
    image_path = '/images/{}'
    opener = urllib.request.URLopener()
    if not os.path.isfile(filename):
        LOGGER.info('Retrieving video from: {}'.format(video_url))
        opener.retrieve(video_url, image_path.format(filename))

    videogen = skvideo.io.vreader(image_path.format(filename))

    chunk = 0
    chunk_name = '{}.mp4'.format(str(uuid.uuid4()))
    writer = skvideo.io.FFmpegWriter(image_path.format(chunk_name))
    for i, frame in enumerate(videogen):
        if i % FRAMES_PER_CHUNK == 0 and i > 0:
            writer.close()
            infer_from_video.delay(chunk_name, filename, chunk * FRAMES_PER_CHUNK)
            chunk += 1
            chunk_name = '{}.mp4'.format(str(uuid.uuid4()))
            writer = skvideo.io.FFmpegWriter(image_path.format(chunk_name))
        writer.writeFrame(frame)
    writer.close()
