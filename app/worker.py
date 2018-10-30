import hashlib
import os
import uuid

import numpy as np
import six.moves.urllib as urllib
import skvideo.io
from celery.utils.log import get_task_logger
from celery.signals import worker_init, worker_process_init
from celery.concurrency import asynpool

from app import celery, db
from app.object_detector import ObjectDetector
from app.models import Video, Frame, Detection


asynpool.PROC_ALIVE_TIMEOUT = 100.0  # set this long enough

LOGGER = get_task_logger(__name__)

FRAMES_PER_CHUNK = os.environ.get('FRAMES_PER_CHUNK', 100)
LEADER_NODE_URL = os.environ.get('LEADER_NODE_URL', 'http://localhost:5000/videos/')
INFERENCE_MODEL = os.environ.get('INFERENCE_MODEL', 'ssdlite_mobilenet_v2_coco_2018_05_09')
DETECTOR = None


def store_frame_metadata(parent_id, frame_ix, metadata, start_ix=0):
    frame = Frame(
        position=(frame_ix + start_ix),
        video_id=parent_id
    )
    db.session.add(frame)
    for i in range(metadata['num_detections']):
        box = metadata['detection_boxes'][i]
        detection = Detection(
            frame=frame,
            y_min=np.asscalar(box[0]),
            x_min=np.asscalar(box[1]),
            y_max=np.asscalar(box[2]),
            x_max=np.asscalar(box[3]),
            object_name=DETECTOR.category_index.get(
                metadata['detection_classes'][i],
                dict()
            ).get('name', 'Unknown'),
            score=np.asscalar(metadata['detection_scores'][i])
        )
        db.session.add(detection)
    db.session.commit()


@worker_process_init.connect()
def on_worker_init(**_):
    global DETECTOR
    DETECTOR = ObjectDetector(INFERENCE_MODEL)
    LOGGER.info('Worker initialized with model')


@celery.task(name='infer_from_video')
def infer_from_video(chunk_name, parent_id, chunk_start_frame):
    LOGGER.info('Started processing video')
    image_path = '/images/{}'
    opener = urllib.request.URLopener()
    chunk_path = image_path.format(chunk_name)
    opener.retrieve(LEADER_NODE_URL + chunk_name, chunk_path)
    output_fn = lambda frame, meta: store_frame_metadata(
        parent_id, frame, meta, chunk_start_frame)
    DETECTOR.run_inference_for_video(chunk_path, output_fn=output_fn)
    LOGGER.info('Finished processing video')


@celery.task(name='split_video')
def split_video(video_id):
    video = Video.query.get(video_id)
    filename = '{}.mp4'.format(hashlib.md5(video.url.encode()).hexdigest())
    image_path = '/images/{}'
    opener = urllib.request.URLopener()
    if not os.path.isfile(filename):
        LOGGER.info('Retrieving video from: {}'.format(video.url))
        opener.retrieve(video.url, image_path.format(filename))

    videogen = skvideo.io.vreader(image_path.format(filename))

    chunk = 0
    chunk_name = '{}.mp4'.format(str(uuid.uuid4()))
    writer = skvideo.io.FFmpegWriter(image_path.format(chunk_name))
    for i, frame in enumerate(videogen):
        if i % FRAMES_PER_CHUNK == 0 and i > 0:
            writer.close()
            infer_from_video.delay(chunk_name, video_id, chunk * FRAMES_PER_CHUNK)
            chunk += 1
            chunk_name = '{}.mp4'.format(str(uuid.uuid4()))
            writer = skvideo.io.FFmpegWriter(image_path.format(chunk_name))
        writer.writeFrame(frame)
    writer.close()
    infer_from_video.delay(chunk_name, video_id, chunk * FRAMES_PER_CHUNK)
