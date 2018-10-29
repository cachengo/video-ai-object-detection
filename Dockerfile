FROM debian:stretch-slim

RUN apt update \
    && apt install -y libatlas-base-dev python3-pip python3-dev

COPY requirements.txt /requirements.txt

RUN pip3 install -r requirements.txt \
    && apt install -y protobuf-compiler python-pil python-lxml python-tk git \
    && git clone https://github.com/tensorflow/models.git \
    && cd models/research/ \
    && protoc object_detection/protos/*.proto --python_out=.

RUN mkdir /images && mkdir /celery && apt install -y ffmpeg

WORKDIR /object-detection
COPY . ./

ENV PYTHONPATH=/models/research:/models/research/slim

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]
