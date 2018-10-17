#!/bin/bash

if [ "$CONTAINER_ROLE" = "server" ];
then
    echo "Role is: $CONTAINER_ROLE";
    cd app;
    python3 server.py;
fi

if [ "$CONTAINER_ROLE" = "inference" ];
then
    echo "Role is: $CONTAINER_ROLE";
    cd app;
    celery -A worker worker -Q inference --loglevel=INFO;
fi

if [ "$CONTAINER_ROLE" = "server_worker" ];
then
    echo "Role is: $CONTAINER_ROLE";
    cd app;
    celery -A worker worker -Q server --loglevel=INFO;
fi
