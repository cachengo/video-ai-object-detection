import hashlib
import time
import os
import uuid

import numpy as np
import six.moves.urllib as urllib
import skvideo.io
from celery.utils.log import get_task_logger
from celery.signals import worker_init, worker_process_init
from celery.concurrency import asynpool

from app import celery, db
from app.models import Video, Frame, Detection, Job


asynpool.PROC_ALIVE_TIMEOUT = 100.0  # set this long enough

LOGGER = get_task_logger(__name__)

FRAMES_PER_CHUNK = os.environ.get('FRAMES_PER_CHUNK', 100)
LEADER_NODE_URL = os.environ.get('LEADER_NODE_URL', 'http://localhost:5000/videos/')
DETECTOR = None
INFERENCE_JOB_DESC = 'Infer'
SPLIT_JOB_DESC = 'Download and Split'


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
    if os.environ.get('CONTAINER_ROLE', '') ==  'inference':
        # This import takes some time and we should avoid it unless necessary
        from app.lite_object_detector import ObjectDetector
        DETECTOR = ObjectDetector()
    LOGGER.info('Worker initialized with model')


@celery.task(name='infer_from_video', bind=True)
def infer_from_video(self, chunk_name, parent_id, chunk_start_frame):
    start_time = time.time()
    image_path = '/images/{}'
    opener = urllib.request.URLopener()
    chunk_path = image_path.format(chunk_name)
    opener.retrieve(LEADER_NODE_URL + chunk_name, chunk_path)
    output_fn = lambda frame, meta: store_frame_metadata(
        parent_id, frame, meta, chunk_start_frame)
    DETECTOR.run_inference_for_video(chunk_path, output_fn=output_fn, job=self)
    job = Job.query.filter_by(celery_id=self.request.id).one()
    job.average_inference_time = (
        self.AsyncResult(self.request.id).info.get('avg_inference_time', 0)
    )
    job.total_job_time = time.time() - start_time
    db.session.add(job)
    db.session.commit()
    LOGGER.info('Finished processing video')


def submit_inference_job(chunk_name, parent_id, start_ix):
    task = infer_from_video.delay(chunk_name, parent_id, start_ix)
    job = Job(
        desc=INFERENCE_JOB_DESC,
        celery_id=task.id,
        video_id=parent_id
    )
    db.session.add(job)
    db.session.commit()


@celery.task(name='split_video', bind=True)
def split_video(self, video_id):
    self.update_state(state='DOWNLOADING')
    video = Video.query.get(video_id)
    filename = '{}.mp4'.format(hashlib.md5(video.url.encode()).hexdigest())
    image_path = '/images/{}'
    opener = urllib.request.URLopener()
    if not os.path.isfile(filename):
        LOGGER.info('Retrieving video from: {}'.format(video.url))
        opener.retrieve(video.url, image_path.format(filename))

    videogen = skvideo.io.FFmpegReader(image_path.format(filename))
    (video_length, _, _, _) = videogen.getShape()
    chunk = 0
    chunk_name = '{}.mp4'.format(str(uuid.uuid4()))
    writer = skvideo.io.FFmpegWriter(image_path.format(chunk_name))
    i = -1
    for frame in videogen.nextFrame():
        i += 1
        if i % FRAMES_PER_CHUNK == 0 and i > 0:
            writer.close()
            submit_inference_job(chunk_name, video_id, chunk * FRAMES_PER_CHUNK)
            self.update_state(state='PROGRESS',
                              meta={'current': i, 'total': video_length}
                             )
            chunk += 1
            chunk_name = '{}.mp4'.format(str(uuid.uuid4()))
            writer = skvideo.io.FFmpegWriter(image_path.format(chunk_name))
        writer.writeFrame(frame)
    writer.close()
    submit_inference_job(chunk_name, video_id, chunk * FRAMES_PER_CHUNK)
    self.update_state(state='PROGRESS',
                      meta={'current': video_length, 'total': video_length}
                     )


def get_status(job):
    if job.desc == SPLIT_JOB_DESC:
        return split_video.AsyncResult(job.celery_id)
    if job.desc == INFERENCE_JOB_DESC:
        return split_video.AsyncResult(job.celery_id)
