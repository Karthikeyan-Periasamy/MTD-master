FROM ubuntu:20.04

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    wget \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev


RUN add-apt-repository ppa:deadsnakes/ppa -y
RUN apt-get update

RUN apt-get install -y python3.12 python3.12-dev python3.12-venv
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Install pip directly for Python 3.12
RUN wget https://bootstrap.pypa.io/get-pip.py && python3 get-pip.py
RUN rm get-pip.py

# Set the working directory inside the container
WORKDIR /session-manager

COPY requirements.txt /session-manager/

RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Install specific dependencies to avoid issues
RUN python3 -m pip install --no-cache-dir six requests urllib3
RUN python3 -m pip install --no-cache-dir -r /session-manager/requirements.txt
RUN pip install urllib3==1.26.16 && pip install urllib3 --no-deps


RUN apt-get clean && rm -rf /var/lib/apt/lists/*


COPY . /session-manager/

# Expose the port the Flask app runs on
EXPOSE 8080

# Command to run the Flask application
CMD ["python3", "/session-manager/serve.py"]



#FROM python:3.8.9-slim-buster
#COPY src/sesssion-manager/ /src/sesssion-manager
#COPY requirements.txt /src/requirements.txt
#RUN pip3 install -r /src/requirements.txt
#CMD ["python3", "/src/session-manager/serve.py"]