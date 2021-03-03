export IMAGE_TAG=$(cat VERSION)
export AARCH=`uname -m`

docker build -t cachengo/video-object-detection-$AARCH:$IMAGE_TAG .
docker push cachengo/video-object-detection-$AARCH:$IMAGE_TAG
