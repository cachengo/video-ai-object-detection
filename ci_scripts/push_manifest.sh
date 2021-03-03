export IMAGE_TAG=$(cat VERSION)

docker manifest create --amend cachengo/video-object-detection:$IMAGE_TAG cachengo/video-object-detection-x86_64:$IMAGE_TAG cachengo/video-object-detection-aarch64:$IMAGE_TAG
docker manifest push cachengo/video-object-detection:$IMAGE_TAG
