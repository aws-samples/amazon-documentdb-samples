FROM node:12-buster

ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ADD action.sh /tmp

RUN apt-get -y update && \
    apt-get install -y lsb-release iproute2 sudo vim curl build-essential && \
    apt-get install -y awscli git zip && \
    chmod 755 /tmp/action.sh

ENTRYPOINT [ "/tmp/action.sh" ]
