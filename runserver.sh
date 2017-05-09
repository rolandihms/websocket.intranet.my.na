fuser -k 8000/tcp
source env/bin/activate
python server.py 2>&1 >>log  &
