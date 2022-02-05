import os
import time

import cv2
import numpy as np
import tflite_runtime.interpreter as tflite

from object_detection.utils import ops as utils_ops
from object_detection.utils import label_map_util


def import_model():

    path_to_labels = os.path.join('/models/research/object_detection/data',
                                  'mscoco_label_map.pbtxt'
                                 )
    armnn_delegate = tflite.load_delegate( 
	library="./libarmnnDelegate.so",
        options={"backends": "CpuAcc,GpuAcc,CpuRef", "logging-severity":"info"}
                                         )

    interpreter = tflite.Interpreter(model_path="./detect.tflite", experimental_delegates=[armnn_delegate])
    interpreter.allocate_tensors()

    category_index = label_map_util.create_category_index_from_labelmap(
        path_to_labels, use_display_name=True)
    return interpreter, category_index


def resize_image(im, desired_size, stretch=False):
    old_size = im.shape[:2] # old_size is in (height, width) format
    if old_size[0] == desired_size and old_size[1] == desired_size:
        return im, (0, 0)

    if stretch:
        return cv2.resize(im, (desired_size, desired_size)), (1, 1)

    ratio = float(desired_size)/max(old_size)
    new_size = tuple([int(x*ratio) for x in old_size])

    # new_size should be in (width, height) format
    im = cv2.resize(im, (new_size[1], new_size[0]))

    delta_w = desired_size - new_size[1]
    delta_h = desired_size - new_size[0]
    top, bottom = delta_h//2, delta_h-(delta_h//2)
    left, right = delta_w//2, delta_w-(delta_w//2)

    color = [0, 0, 0]
    new_im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return new_im, (delta_w/desired_size, delta_h/desired_size)


def adjust_position(position, border_size):
    return min(max((position - border_size/2)/(1 - border_size), 0), 1)


class ObjectDetector:

    def __init__(self):
        self.graph, self.category_index = import_model()

    def run_inference_for_single_image(self, image):
        graph = self.graph
        input_details = graph.get_input_details()
        output_details = graph.get_output_details()

        input_data, border_sizes = resize_image(image, 300)
        # TODO: Not all models take in float32. Quantized likes uint8
        graph.set_tensor(input_details[0]['index'], [(input_data/255).astype('float32')])
        graph.invoke()

        boxes = graph.get_tensor(output_details[0]['index'])[0]
        boxes = [
            [adjust_position(box[0], border_sizes[1]),
             adjust_position(box[1], border_sizes[0]),
             adjust_position(box[2], border_sizes[1]),
             adjust_position(box[3], border_sizes[0])
            ] for box in boxes
        ]

        #After moving to TFLite, class predictions become off-by-one
        output_dict = {
            'detection_boxes': np.array(boxes),
            'detection_classes': 1 + graph.get_tensor(output_details[1]['index'])[0].astype(np.uint8),
            'detection_scores':graph.get_tensor(output_details[2]['index'])[0],
            'num_detections': int(graph.get_tensor(output_details[3]['index'])[0])
        }

        return output_dict

    def run_inference_for_video(self, video_path, output_fn=None, job=None):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise "Error opening video stream or file"
        video_length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_inference_time = 0

        frame_num = -1
        while cap.isOpened():
            ret, frame = cap.read()
            if ret:
                frame_num += 1
                t_start_inference = time.time()
                output_dict = self.run_inference_for_single_image(frame)
                total_inference_time += time.time() - t_start_inference
                if output_fn:
                    output_fn(frame_num, output_dict)
                if job:
                    job.update_state(state='PROGRESS',
                                     meta={
                                         'current': frame_num,
                                         'total': video_length,
                                         'avg_inference_time': total_inference_time/(frame_num+1)
                                     }
                                    )
            else:
                break
        print('Finished video')

