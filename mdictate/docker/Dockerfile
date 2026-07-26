FROM public.ecr.aws/docker/library/python:3-alpine
# openssl: self-signed HTTPS cert for browser mic (secure context on LAN IPs)
RUN apk add --no-cache openssl
ADD code /code
WORKDIR /code
RUN pip install --no-cache-dir -r requirements.txt
ENV STT_HOST=0.0.0.0 \
    STT_PORT=5000 \
    STT_SSL=1 \
    DEFAULT_WHISPER_URL=http://localhost:8025
EXPOSE 5000
CMD ["python", "app.py"]
