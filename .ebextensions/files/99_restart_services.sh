#!/bin/bash

set -xe

# check if we already have the celeryd service
/usr/local/bin/supervisorctl -c /opt/python/etc/supervisord.conf status | grep websocket
if [[ $? ]]; then
  /usr/local/bin/supervisorctl -c /opt/python/etc/supervisord.conf restart websocket
fi

eventHelper.py --msg "Application server successfully restarted." --severity INFO