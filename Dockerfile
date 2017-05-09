FROM ubuntu

MAINTAINER Roland Ihms <rolandihms@gmail.com>

RUN apt-get update -y && apt-get install git python python-pip -y
RUN cd /tmp \
    && git clone https://github.com/rolandihms/websocket.intranet.my.na.git \
    && cd websocket.intranet.my.na \
    && pip install tornado

EXPOSE 8888

CMD ["python", "/server.py"]
