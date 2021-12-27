import os
import tarfile
import time

import numpy as np
import tflite_runtime as tf
import six.moves.urllib as urllib
import skvideo.io


from object_detection.utils import ops as utils_ops
from object_detection.utils import label_map_util


def import_model(model_name):

    model_file = model_name + '.tar.gz'
    download_base = 'http://download.tensorflow.org/models/object_detection/'
    path_to_graph = model_name + '/frozen_inference_graph.pb'
    path_to_labels = os.path.join('/models/research/object_detection/data',
                                  'mscoco_label_map.pbtxt'
                                 )

    if not os.path.isfile(path_to_graph):
        opener = urllib.request.URLopener()
        print(download_base + model_file)
        opener.retrieve(download_base + model_file, model_file)
        tar_file = tarfile.open(model_file)
        for file in tar_file.getmembers():
            file_name = os.path.basename(file.name)
            if 'frozen_inference_graph.pb' in file_name:
                tar_file.extract(file, os.getcwd())

    graph = tf.Graph()
    with graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.GFile(path_to_graph, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')

    category_index = label_map_util.create_category_index_from_labelmap(
        path_to_labels, use_display_name=True)
    return graph, category_index


class ObjectDetector:

    def __init__(self, model_name):
        self.graph, self.category_index = import_model(model_name)

    def get_tensor_dict(self, image):
        with self.graph.as_default():
            ops = tf.get_default_graph().get_operations()
            all_tensor_names = {output.name for op in ops for output in op.outputs}
            tensor_dict = {}
            for key in ['num_detections', 'detection_boxes', 'detection_scores',
                        'detection_classes', 'detection_masks'
                       ]:
                tensor_name = key + ':0'
                if tensor_name in all_tensor_names:
                    tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(
                        tensor_name)
            if 'detection_masks' in tensor_dict:
                # The following processing is only for single image
                detection_boxes = tf.squeeze(tensor_dict['detection_boxes'], [0])
                detection_masks = tf.squeeze(tensor_dict['detection_masks'], [0])
                # Reframe is required to translate mask from box coordinates to
                # image coordinates and fit the image size.
                real_num_detection = tf.cast(tensor_dict['num_detections'][0], tf.int32)
                detection_boxes = tf.slice(detection_boxes, [0, 0], [real_num_detection, -1])
                detection_masks = tf.slice(detection_masks, [0, 0, 0], [real_num_detection, -1, -1])
                detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
                    detection_masks, detection_boxes, image.shape[0], image.shape[1])
                detection_masks_reframed = tf.cast(
                    tf.greater(detection_masks_reframed, 0.5), tf.uint8)
                # Follow the convention by adding back the batch dimension
                tensor_dict['detection_masks'] = tf.expand_dims(
                    detection_masks_reframed, 0)
        return tensor_dict

    def run_inference_for_single_image(self, image, tensor_dict=None):
        with self.graph.as_default():
            with tf.Session() as sess:
                # Get handles to input and output tensors
                tensor_dict = tensor_dict or self.get_tensor_dict(image)
                image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')

                # Run inference
                output_dict = sess.run(
                    tensor_dict,
                    feed_dict={image_tensor: np.expand_dims(image, 0)}
                )
                output_dict['num_detections'] = int(output_dict['num_detections'][0])
                output_dict['detection_classes'] = output_dict[
                    'detection_classes'][0].astype(np.uint8)
                output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
                output_dict['detection_scores'] = output_dict['detection_scores'][0]
                if 'detection_masks' in output_dict:
                    output_dict['detection_masks'] = output_dict['detection_masks'][0]
        return output_dict

    def run_inference_for_video(self, video_path, output_fn=None, job=None):
        tensor_dict = None
        videogen = skvideo.io.FFmpegReader(video_path)
        (video_length, _, _, _) = videogen.getShape()
        total_inference_time = 0

        frame_num = -1
        for frame in videogen.nextFrame():
            frame_num += 1
            image_np = np.array(frame).astype('uint8')
            tensor_dict = tensor_dict or self.get_tensor_dict(image_np)
            t_start_inference = time.time()
            output_dict = self.run_inference_for_single_image(
                image_np,
                tensor_dict=tensor_dict
            )
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
