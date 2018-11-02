from flask import request, render_template, send_from_directory, redirect, \
    url_for, jsonify

from app import app, db
from app.worker import split_video, get_status, SPLIT_JOB_DESC
from app.models import Job, Video, Frame




class InvalidUsage(Exception):

    def __init__(self, message, status_code=400, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        result = dict(self.payload or ())
        result['message'] = self.message
        return result


@app.route('/start_job', methods=['GET', 'POST'])
def initiate_video():
    if request.method == 'POST':
        data = request.form
        if 'video_name' not in data or 'video_url' not in data:
            raise InvalidUsage('Data must contain video_name and video_url')
        video = Video(name=data['video_name'], url=data['video_url'])
        db.session.add(video)
        db.session.commit()
        task = split_video.delay(video.id)
        job = Job(
            desc=SPLIT_JOB_DESC,
            celery_id=task.id,
            video=video
        )
        db.session.add(job)
        db.session.commit()
        return redirect(url_for('jobs', video_id=video.id))
    return render_template('submit_job.html')


@app.route('/', methods=['GET', 'POST'])
@app.route('/all_videos')
def all_videos():
    videos = Video.query.all()
    return render_template('all_videos.html', videos=videos)


@app.route('/results/<video_id>')
def results(video_id):
    video = Video.query.get(video_id)
    return render_template('results.html', video=video)


@app.route('/detections/<video_id>/<frame_ix>')
def detections(video_id, frame_ix):
    frame = Frame.query.filter_by(video_id=video_id, position=frame_ix).one()
    result = [{
        'y_min': detection.y_min,
        'x_min': detection.x_min,
        'y_max': detection.y_max,
        'x_max': detection.x_max,
        'object_name': detection.object_name,
        'score': detection.score
    } for detection in frame.detections]
    return jsonify(result)


@app.route('/progress/<video_id>')
def jobs(video_id):
    video = Video.query.get(video_id)
    jobs = [(job.desc, get_status(job)) for job in video.jobs]
    return render_template('video_progress.html', video=video, jobs=jobs)


@app.route('/videos/<path>')
def images(path):
    # send_static_file will guess the correct MIME type
    print(path)
    return send_from_directory('/images/', path)
