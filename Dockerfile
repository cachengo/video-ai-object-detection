FROM cachengo/tensorflow-cpu:1.12.0-rc1

COPY requirements.txt /requirements.txt
COPY matplotlib-3.0.1-cp36-cp36m-linux_aarch64.whl /matplotlib-3.0.1-cp36-cp36m-linux_aarch64.whl
COPY scikit_image-0.16.2-cp36-cp36m-linux_aarch64.whl /scikit_image-0.16.2-cp36-cp36m-linux_aarch64.whl 
COPY MarkupSafe-2.0.1-cp36-cp36m-manylinux_2_17_aarch64.manylinux2014_aarch64.whl /MarkupSafe-2.0.1-cp36-cp36m-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
COPY tensorflow-1.15.5-cp36-cp36m-linux_aarch64.whl /tensorflow-1.15.5-cp36-cp36m-linux_aarch64.whl
COPY protoc /protoc
COPY gpu_drivers /gpu_drivers

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update \
    && apt install -y python-pil python-lxml python-tk git libpq-dev libfreetype6-dev pkg-config \
    && pip3 install --upgrade pip && python3.6 -m pip install --upgrade setuptools \
    && pip3 install /matplotlib-3.0.1-cp36-cp36m-linux_aarch64.whl \
    && pip3 install /scikit_image-0.16.2-cp36-cp36m-linux_aarch64.whl \
    && pip3 install -r requirements.txt \
    && pip3 install opencv-python --no-deps \
    && pip3 install /tensorflow-1.15.5-cp36-cp36m-linux_aarch64.whl \
    && pip3 install tensorflow-object-detection-api --no-deps && pip3 install tf-slim==1.0.0 && pip3 install --extra-index-url https://google-coral.github.io/py-repo/ tflite_runtime \
    && git clone https://github.com/tensorflow/models.git \
    && cd models/research/ \
    && cp /protoc /usr/local/bin/ \
    && protoc object_detection/protos/*.proto --python_out=. \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && dpkg -i /gpu_drivers/rockchip-mali-midgard14_1.6-2_arm64.deb \
    && dpkg -i /gpu_drivers/rockchip-mali-midgard-dev_1.6-2_arm64.deb \
    && apt install -f

RUN mkdir /images \
	  && mkdir /celery \
    && apt-get update \
	  && apt-get install -y ffmpeg libavcodec-dev libavformat-dev libavdevice-dev \
          && pip3 install --force-reinstall protobuf \
          && pip3 install --force-reinstall matplotlib --no-deps 
	 # && git clone https://github.com/opencv/opencv.git \
	 # && cd /opencv \
   # && git checkout 3.3.0 \
   # && mkdir build \
   # && cd build \
   # && cmake -D CMAKE_BUILD_TYPE=RELEASE -D WITH_FFMPEG=ON .. \
   # && make install \
   # && mkdir -p /usr/local/opencv \
   # && cp -r /opencv/build/lib /usr/local/opencv/lib \
   # && rm -rf /opencv \
   # && apt-get clean \
   # && rm -rf /var/lib/apt/lists/*
#
WORKDIR /object-detection
COPY . ./
RUN cp -r /object-detection/armnn /

ENV PYTHONPATH=/models/research:/models/research/slim:/usr/local/opencv/lib
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV LD_LIBRARY_PATH="/armnn/build/"

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]
