from app import db


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(240), index=False)
    name = db.Column(db.String(32), index=False)
    video_frames = db.relationship('Frame', backref='video', lazy='dynamic')
    jobs = db.relationship('Job', backref='video', lazy='dynamic')


class Frame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.Integer, index=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), index=True)
    detections = db.relationship('Detection', backref='frame', lazy='dynamic')


class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    frame_id = db.Column(db.Integer, db.ForeignKey('frame.id'), index=True)
    y_min = db.Column(db.Float, index=False)
    x_min = db.Column(db.Float, index=False)
    y_max = db.Column(db.Float, index=False)
    x_max = db.Column(db.Float, index=False)
    object_name = db.Column(db.String(32), index=False)
    score = db.Column(db.Float, index=False)


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    desc = db.Column(db.String(32))
    celery_id = db.Column(db.String(48), index=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), index=True)
    average_inference_time = db.Column(db.Float, index=False)
    total_job_time = db.Column(db.Float, index=False)
