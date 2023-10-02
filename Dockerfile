FROM python:3.11.3-slim-bullseye

ENV PYTHONUNBUFFERED 1
ENV PATH=/root/.local/bin:$PATH

# install requirements
COPY requirements.txt /requirements.txt
RUN pip install --user -r requirements.txt

# setup app
RUN mkdir /app /data
COPY app/ /app

# start
VOLUME /data
WORKDIR /app

# run
RUN chmod +x ./run.sh
CMD ["./run.sh"]
