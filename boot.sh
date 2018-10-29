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
    celery -A app.celery worker -Q inference --loglevel=INFO;
fi

if [ "$CONTAINER_ROLE" = "server_worker" ];
then
    echo "Role is: $CONTAINER_ROLE";
    celery -A app.celery worker -Q server --loglevel=INFO;
fi
