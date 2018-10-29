import hashlib
import os
import uuid

import six.moves.urllib as urllib
import skvideo.io
from celery.utils.log import get_task_logger
from celery.signals import worker_init, worker_process_init
from celery.concurrency import asynpool

from app import celery
from app.object_detector import ObjectDetector


asynpool.PROC_ALIVE_TIMEOUT = 100.0  # set this long enough

LOGGER = get_task_logger(__name__)

FRAMES_PER_CHUNK = os.environ.get('FRAMES_PER_CHUNK', 100)
LEADER_NODE_URL = os.environ.get('LEADER_NODE_URL', 'http://localhost:5000/videos/')
INFERENCE_MODEL = os.environ.get('INFERENCE_MODEL', 'ssdlite_mobilenet_v2_coco_2018_05_09')
DETECTOR = None


def store_frame_metadata(video_name, frame_number, metadata, start_frame=0):
    pass

@worker_process_init.connect()
def on_worker_init(**_):
    global DETECTOR
    DETECTOR = ObjectDetector(INFERENCE_MODEL)
    LOGGER.info('Worker initialized with model')


@celery.task(name='infer_from_video')
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


@celery.task(name='split_video')
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
