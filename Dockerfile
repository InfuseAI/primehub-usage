FROM python:3.10-slim

ENV LANG=C.UTF-8
ADD requirements.txt /src/requirements.txt
RUN pip install -r /src/requirements.txt

ADD alembic.ini /src/alembic.ini
ADD alembic /src/alembic
ADD setup.py /src/setup.py
ADD usage /src/usage
ADD scripts /src/scripts

WORKDIR /src
RUN mkdir -p /app && python setup.py install
