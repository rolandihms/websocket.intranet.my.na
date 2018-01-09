#!/usr/bin/env bash
set -e

SCRIPT_PATH=`dirname $0`

source $SCRIPT_PATH/utils.sh
# Check for leader: see utils.sh
if is_leader; then
  echo "Start leader deploy"
else
  echo "Start non-leader deploy"
fi

# copy websocket app config
copy_ext $SCRIPT_PATH/files/websocket.conf /opt/python/etc/websocket.conf 0755 root root
# copy restart hook to different hooks folders
copy_ext $SCRIPT_PATH/files/99_restart_services.sh /opt/elasticbeanstalk/hooks/appdeploy/enact/99_restart_services.sh 0755 root root
copy_ext $SCRIPT_PATH/files/99_restart_services.sh /opt/elasticbeanstalk/hooks/configdeploy/enact/99_restart_services.sh 0755 root root
copy_ext $SCRIPT_PATH/files/99_restart_services.sh /opt/elasticbeanstalk/hooks/restartappserver/enact/99_restart_services.sh 0755 root root

# include celeryd.conf into the supervisord.conf
script_add_line /opt/python/etc/supervisord.conf "include" "[include]"
script_add_line /opt/python/etc/supervisord.conf "websocket.conf" "files=websocket.conf "

# Reread the supervisord config
supervisorctl -c /opt/python/etc/supervisord.conf reread
# Update supervisord in cache without restarting all services
supervisorctl -c /opt/python/etc/supervisord.conf update
# Start/Restart celeryd through supervisord
supervisorctl -c /opt/python/etc/supervisord.conf restart websocket