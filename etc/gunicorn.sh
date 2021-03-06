#!/bin/bash
set -e
LOGFILE=/var/log/rules/gunicorn.log
LOGDIR=$(dirname $LOGFILE)
NUM_WORKERS=3
# user/group to run as
USER=root
GROUP=root
cd /usr/local/django/rules/rules
source /usr/local/django/rules/bin/activate
test -d $LOGDIR || mkdir -p $LOGDIR
exec /usr/local/django/rules/bin/python /usr/local/django/rules/bin/gunicorn_django -w $NUM_WORKERS --user=$USER --group=$GROUP --log-level=debug --log-file=$LOGFILE 2>>$LOGFILE -b 0.0.0.0:8000