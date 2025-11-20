FROM python:3.11-slim

# 1. Systemowe zależności (ffmpeg + nagłówki libav + kompilator)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    pkg-config \
    build-essential \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
 && rm -rf /var/lib/apt/lists/*

# 2. Katalog roboczy
WORKDIR /app

# 3. Najpierw requirements (lepszy cache Dockera)
COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

# 4. Potem reszta kodu
COPY . .

# 5. Start aplikacji
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
