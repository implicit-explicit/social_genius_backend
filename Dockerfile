FROM alpine:3.3

RUN apk add --update \
    py-pip \
    python3 \
&& rm -rf /var/cache/apk/*

COPY src /opt/
RUN pip install -r /opt/src/requirements.txt
