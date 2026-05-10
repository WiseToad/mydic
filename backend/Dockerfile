FROM python:3.14-slim

WORKDIR /app

# ffmpeg is for offline wav-to-lossy worker
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic alembic/
COPY alembic.ini .

COPY app app/

COPY encode-tts.py start.sh users.py .
RUN chmod +x encode-tts.py start.sh users.py

EXPOSE 8000
CMD /app/start.sh
