#!/bin/bash

a_flag="";
r_flag="";
print_usage() {
  printf "Usage: ...";
}

while getopts 'ar' flag; do
  case "${flag}" in
    a) a_flag="true" ;;
    r) r_flag="true" ;;
    *) print_usage
       exit 1 ;;
  esac
done


if [ "$a_flag" = "true" ];
then
  echo "a_flag is $a_flag"
  docker network create -d bridge video-ai;

  docker stop redis;
  docker rm redis;
  docker run -d \
    --name redis \
    --net=video-ai \
    -p 6379:6379 \
    redis:alpine;

  docker stop postgres;
  docker rm postgres;
  docker run -d \
    --name postgres \
    --net video-ai \
    -p 5432:5432 \
    -e POSTGRES_PASSWORD=password \
    postgres
fi

export IMAGE_TAG=$(cat VERSION);
export AARCH=`uname -m`;

if [ "$r_flag" = "true" ];
then
    docker build -t cachengo/video-object-detection-$AARCH:$IMAGE_TAG .
fi

docker stop detection_main;
docker rm detection_main;


docker stop detection_main;
docker rm detection_main;
docker run -d \
  -p 5000:5000 \
  -e CELERY_BROKER_URL=redis://redis:6379 \
  -e CELERY_RESULT_BACKEND=redis://redis:6379 \
  -e CONTAINER_ROLE=server \
  -e DATABASE_URL='postgresql://postgres:password@postgres:5432/postgres' \
  -v /images:/images \
  --net=video-ai \
  --name detection_main \
  cachengo/video-object-detection-$AARCH:$IMAGE_TAG;


docker stop inference_worker;
docker rm inference_worker;
docker run -d \
  -e CELERY_BROKER_URL=redis://redis:6379 \
  -e CELERY_RESULT_BACKEND=redis://redis:6379 \
  -e CONTAINER_ROLE=inference \
  -e LEADER_NODE_URL=http://detection_main:5000/videos/ \
  -e INFERENCE_MODEL=ssdlite_mobilenet_v2_coco_2018_05_09 \
  -e DATABASE_URL='postgresql://postgres:password@postgres:5432/postgres' \
  --name inference_worker \
  --net=video-ai \
  --dns=8.8.8.8 \
  --cpus=1 \
  cachengo/video-object-detection-$AARCH:$IMAGE_TAG;


docker stop server_worker;
docker rm server_worker;
docker run -d \
  -e CELERY_BROKER_URL=redis://redis:6379 \
  -e CELERY_RESULT_BACKEND=redis://redis:6379 \
  -e CONTAINER_ROLE=server_worker \
  -e DATABASE_URL='postgresql://postgres:password@postgres:5432/postgres' \
  -v /images:/images \
  --net=video-ai \
  --name server_worker \
  --dns=8.8.8.8 \
  --cpus=1 \
  cachengo/video-object-detection-$AARCH:$IMAGE_TAG;
