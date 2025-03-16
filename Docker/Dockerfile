FROM debian:stable-slim

LABEL version="1.0.0"
LABEL description="OpenManus Docker Image"

# Download and install required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libsqlite3-dev \
    libreadline-dev \
    libffi-dev \
    curl \
    libbz2-dev \
    git \
    ca-certificates

# Download, Build and install Python 3.12
RUN wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz \
    && tar -xf Python-3.12.0.tgz \
    && cd Python-3.12.0 \
    && ./configure --enable-optimizations --with-ensurepip=install \
    && make -j $(nproc) \
    && make altinstall \
    && cd .. \
    && rm -rf Python-3.12.0 Python-3.12.0.tgz

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.12 1 \
    && update-alternatives --set python3 /usr/local/bin/python3.12 \
    && update-alternatives --install /usr/bin/pip3 pip3 /usr/local/bin/pip3.12 1 \
    && update-alternatives --set pip3 /usr/local/bin/pip3.12

# Clean up build dependencies
RUN apt-get purge -y \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libsqlite3-dev \
    libreadline-dev \
    libffi-dev \
    libbz2-dev \
    wget \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
if [ ! -f main.py ]; then\n\
    echo "Cloning repository..."\n\
    git clone https://github.com/mannaandpoem/OpenManus.git ./\n\
fi\n\
\n\
if ! git config --get-regexp safe.directory | grep -q /app/OpenManus; then\n\
    git config --global --add safe.directory /app/OpenManus\n\
fi\n\
\n\
if [ ! -d config ]; then\n\
    mkdir -p config\n\
fi\n\
\n\
if [ ! -f config/config.toml ]; then\n\
    echo "Copying config from example..."\n\
    cp config/config.example.toml config/config.toml\n\
fi\n\
\n\
pip3 install --user -r requirements.txt\n\
\n\
if [ "$1" = "dev" ]; then\n\
    echo "Running in development mode..."\n\
    python3 run_flow.py\n\
else\n\
    echo "Launching OpenManus..."\n\
    python3 main.py\n\
fi' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Create user for running the application
RUN useradd -m openmanususer && \
    mkdir -p /app/OpenManus && \
    chown -R openmanususer:openmanususer /app/OpenManus

# Switch to non-root user
USER openmanususer

# Upgrade pip and clean cache
RUN pip3 install --user --upgrade pip && \
    pip3 cache purge

# Set working directory
WORKDIR /app/OpenManus

# Default command
ENTRYPOINT ["/entrypoint.sh"]
