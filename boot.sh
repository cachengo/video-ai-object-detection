#!/bin/bash

if [ "$CONTAINER_ROLE" = "server" ];
then
    echo "Role is: $CONTAINER_ROLE";
    flask db upgrade
    exec gunicorn -b :5000 --access-logfile - --error-logfile - server:app
fi

if [ "$CONTAINER_ROLE" = "inference" ];
then
    echo "Role is: $CONTAINER_ROLE";
    INFERENCE_MODEL=${INFERENCE_MODEL:-ssdlite_mobilenet_v2_coco_2018_05_09}
    wget http://download.tensorflow.org/models/object_detection/$INFERENCE_MODEL.tar.gz
    tar -xzvf $INFERENCE_MODEL.tar.gz

    if [ ! -f $(pwd)/$INFERENCE_MODEL/tflite_graph.pb ];
    then
      python3 /models/research/object_detection/export_tflite_ssd_graph.py \
        --pipeline_config_path=$(pwd)/$INFERENCE_MODEL/pipeline.config \
        --trained_checkpoint_prefix=$(pwd)/$INFERENCE_MODEL/model.ckpt \
        --output_directory=$(pwd) \
        --add_postprocessing_op=true

      toco \
        --graph_def_file $(pwd)/tflite_graph.pb \
        --output_file $(pwd)/detect.tflite \
        --input_shapes 1,300,300,3 \
        --input_arrays=normalized_input_image_tensor \
        --output_arrays='TFLite_Detection_PostProcess','TFLite_Detection_PostProcess:1','TFLite_Detection_PostProcess:2','TFLite_Detection_PostProcess:3'  \
        --inference_type FLOAT \
        --allow_custom_ops
    else
      toco \
        --graph_def_file $(pwd)/$INFERENCE_MODEL/tflite_graph.pb \
        --output_file /detect.tflite \
        --input_shapes 1,300,300,3 \
        --input_arrays normalized_input_image_tensor \
        --output_arrays 'TFLite_Detection_PostProcess','TFLite_Detection_PostProcess:1','TFLite_Detection_PostProcess:2','TFLite_Detection_PostProcess:3' \
        --inference_type QUANTIZED_UINT8 \
        --mean_values 128 \
        --std_dev_values 128 \
        --change_concat_input_ranges false \
        --allow_custom_ops
    fi
    celery -A app.celery worker -Q inference --loglevel=INFO -c 1;
fi

if [ "$CONTAINER_ROLE" = "server_worker" ];
then
    echo "Role is: $CONTAINER_ROLE";
    celery -A app.celery worker -Q server --loglevel=INFO -c 1;
fi
