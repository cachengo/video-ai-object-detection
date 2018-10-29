from flask import request, render_template, send_from_directory

from app import app
from app.worker import split_video


@app.route('/', methods=['GET', 'POST'])
def initiate_video():
    if request.method == 'POST':
        data = request.form
        print(data)
        split_video.delay(data['video_url'])
        return 'Video submitted'
    return render_template('submit_job.html', title='Video Analysis')


@app.route('/videos/<path>')
def images(path):
    # send_static_file will guess the correct MIME type
    print(path)
    return send_from_directory('/images/', path)
