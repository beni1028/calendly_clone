FROM python:3.9-alpine

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

RUN apk add -u zlib-dev jpeg-dev gcc musl-dev python3-dev
RUN apk add build-base


RUN python -m pip install --upgrade pip
RUN pip install wheel

COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

