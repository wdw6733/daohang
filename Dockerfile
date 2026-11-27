FROM python:3.12-alpine
RUN apk add --no-cache docker-cli
WORKDIR /app
COPY server.py /app/server.py
COPY netbird-status.py /app/netbird_status.py
COPY site /app/site
EXPOSE 8080
CMD ["python3", "/app/server.py"]
