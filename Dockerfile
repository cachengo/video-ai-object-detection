FROM cachengo/tensorflow-cpu:1.12.0-rc1

COPY requirements.txt /requirements.txt

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update \
    && apt install -y python-pil python-lxml python-tk git libpq-dev libfreetype6-dev pkg-config\
    && pip3 install -r requirements.txt \
    && git clone https://github.com/tensorflow/models.git \
    && cd models/research/ \
    && protoc object_detection/protos/*.proto --python_out=. \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /images \
	  && mkdir /celery \
    && apt-get update \
	  && apt-get install -y ffmpeg libavcodec-dev libavformat-dev libavdevice-dev \
	  && git clone https://github.com/opencv/opencv.git \
	  && cd /opencv \
    && git checkout 3.3.0 \
    && mkdir build \
    && cd build \
    && cmake -D CMAKE_BUILD_TYPE=RELEASE -D WITH_FFMPEG=ON .. \
    && make install \
    && mkdir -p /usr/local/opencv \
    && cp -r /opencv/build/lib /usr/local/opencv/lib \
    && rm -rf /opencv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /object-detection
COPY . ./

ENV PYTHONPATH=/models/research:/models/research/slim:/usr/local/opencv/lib
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]
