import os

from object_detector import ObjectDetector

PATH_TO_TEST_IMAGES_DIR = '/home/lafonj/images'
VIDEO_NAME = '890b8900-a9c0-47d7-b899-a9ac3a63f240.mp4'
TEST_VIDEO_PATH = os.path.join(PATH_TO_TEST_IMAGES_DIR, VIDEO_NAME)

model_name = 'ssdlite_mobilenet_v2_coco_2018_05_09'
detector = ObjectDetector(model_name)
detector.run_inference_for_video(TEST_VIDEO_PATH)