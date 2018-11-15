import os
import time

import numpy as np
import tensorflow.contrib.lite
import skvideo.io
from skimage.transform import resize


from object_detection.utils import ops as utils_ops
from object_detection.utils import label_map_util


def import_model():

    path_to_labels = os.path.join('/models/research/object_detection/data',
                                  'mscoco_label_map.pbtxt'
                                 )

    interpreter = tensorflow.contrib.lite.Interpreter(model_path="./detect.tflite")
    interpreter.allocate_tensors()

    category_index = label_map_util.create_category_index_from_labelmap(
        path_to_labels, use_display_name=True)
    return interpreter, category_index


class ObjectDetector:

    def __init__(self):
        self.graph, self.category_index = import_model()

    def run_inference_for_single_image(self, image):
        graph = self.graph
        input_details = graph.get_input_details()
        output_details = graph.get_output_details()
        # TODO: Not all models take in float32. Quantized likes uint8
        input_data = resize(image, [300, 300], anti_aliasing=True).astype('float32')
        graph.set_tensor(input_details[0]['index'], [input_data.copy()])
        graph.invoke()

        #After moving to TFLite, class predictions become off-by-one
        output_dict = {
            'detection_boxes': graph.get_tensor(output_details[0]['index'])[0],
            'detection_classes': 1 + graph.get_tensor(output_details[1]['index'])[0].astype(np.uint8),
            'detection_scores':graph.get_tensor(output_details[2]['index'])[0],
            'num_detections': int(graph.get_tensor(output_details[3]['index'])[0])
        }

        return output_dict

    def run_inference_for_video(self, video_path, output_fn=None, job=None):
        videogen = skvideo.io.FFmpegReader(video_path)
        (video_length, _, _, _) = videogen.getShape()
        total_inference_time = 0

        frame_num = -1
        for frame in videogen.nextFrame():
            frame_num += 1
            image_np = np.array(frame).astype('uint8')
            t_start_inference = time.time()
            output_dict = self.run_inference_for_single_image(image_np)
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
        print('Finished video')
