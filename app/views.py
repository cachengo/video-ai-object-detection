from flask import request, render_template, send_from_directory

from app import app, db
from app.worker import split_video
from app.models import Video




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


@app.route('/', methods=['GET', 'POST'])
def initiate_video():
    if request.method == 'POST':
        data = request.form
        if 'video_name' not in data or 'video_url' not in data:
            raise InvalidUsage('Data must contain video_name and video_url')
        video = Video(name=data['video_name'], url=data['video_url'])
        db.session.add(video)
        db.session.flush()
        task = split_video.delay(video.id)
        video.ingest_job = task.id
        db.session.add(video)
        db.session.commit()
        return 'Video submitted'
    return render_template('submit_job.html', title='Video Analysis')


@app.route('/videos/<path>')
def images(path):
    # send_static_file will guess the correct MIME type
    print(path)
    return send_from_directory('/images/', path)
