from app import db


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(240), index=False)
    frames = db.relationship('Frame', backref='video', lazy='dynamic')

class Frame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video = db.Column(db.Integer, db.ForeignKey('video.id'))
    position = db.Column(db.Integer, index=True)
    detections = db.relationship('Detection', backref='frame', lazy='dynamic')


class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    box_corner_1 = db.Column(db.Integer, index=False)
    box_corner_2 = db.Column(db.Integer, index=False)
    object_name = db.Column(db.String(32), index=False)
    score = db.Column(db.Float, index=False)
