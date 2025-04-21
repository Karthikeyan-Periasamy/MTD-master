FROM ubuntu:20.04

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Update package lists and install dependencies
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

# Install Python 3.12 and required packages
RUN apt-get install -y python3.12 python3.12-dev python3.12-venv

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Install pip directly for Python 3.12
RUN wget https://bootstrap.pypa.io/get-pip.py && python3 get-pip.py
RUN rm get-pip.py

WORKDIR /webapp1

COPY requirements.txt /webapp/

RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Install specific dependencies to avoid issues
RUN python3 -m pip install --no-cache-dir six requests urllib3


RUN python3 -m pip install --no-cache-dir -r /webapp/requirements.txt

RUN pip install urllib3==1.26.16 && pip install urllib3 --no-deps

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . /webapp1/

EXPOSE 8080

CMD ["python3", "/webapp1/enhanced_serve.py"]
