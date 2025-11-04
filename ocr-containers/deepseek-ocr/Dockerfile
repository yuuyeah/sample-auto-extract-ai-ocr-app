FROM pytorch/pytorch:2.6.0-cuda11.8-cudnn9-devel

# Environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/opt/ml/code:${PATH}"

WORKDIR /opt/ml/code

# Install system packages and Python 3.12
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    wget \
    curl \
    git \
    build-essential \
    ninja-build \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    libgomp1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Create Python command symbolic links
RUN ln -sf /usr/bin/python3.12 /usr/bin/python && \
    ln -sf /usr/bin/python3.12 /usr/bin/python3

# Upgrade pip
RUN python -m pip install --no-cache-dir --upgrade pip

# Install PyTorch with specific versions as per DeepSeek OCR requirements
RUN pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0

# Install vllm for CUDA 11.8
RUN pip install vllm==0.8.5 --extra-index-url https://download.pytorch.org/whl/cu118

# Install remaining Python packages
COPY requirements.txt /opt/ml/code/
RUN pip install --no-cache-dir -r requirements.txt

# Install flash-attn with specific version
RUN pip install --no-cache-dir --no-build-isolation flash-attn==2.7.3

# Copy inference code
COPY app.py model_handler.py /opt/ml/code/

# Expose SageMaker port
EXPOSE 8080

# Start application
ENTRYPOINT ["python", "/opt/ml/code/app.py"]