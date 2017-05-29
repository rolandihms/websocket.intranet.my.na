FROM ubuntu

MAINTAINER Roland Ihms <rolandihms@gmail.com>

RUN apt-get update -y && apt-get install git python python-pip -y && apt-get -y install python-mysqldb
RUN cd /tmp \
    && git clone https://github.com/rolandihms/websocket.intranet.my.na.git \
    && cd websocket.intranet.my.na \
    && pip install tornado

EXPOSE 8000

CMD ["python", "/tmp/websocket.intranet.my.na/server.py"]
