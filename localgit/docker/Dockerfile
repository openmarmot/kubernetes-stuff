FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    git \
    nginx \
    fcgiwrap \
    python3 \
    python3-pip \
    python3-venv \
    spawn-fcgi \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY code/requirements.txt .
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

COPY code/app.py .
COPY code/nginx.conf /etc/nginx/nginx.conf
COPY code/start.sh /start.sh
RUN chmod +x /start.sh

RUN mkdir -p /git && chown -R www-data:www-data /git

EXPOSE 5000

CMD ["/start.sh"]
