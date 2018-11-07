FROM cachengo/tensorflow-cpu:1.12.0-rc1

COPY requirements.txt /requirements.txt

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update \
    && apt install -y python-pil python-lxml python-tk git libpq-dev \
    && pip3 install -r requirements.txt \
    && git clone https://github.com/tensorflow/models.git \
    && cd models/research/ \
    && protoc object_detection/protos/*.proto --python_out=. \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /images && mkdir /celery && apt install -y ffmpeg

WORKDIR /object-detection
COPY . ./

ENV PYTHONPATH=/models/research:/models/research/slim
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]
