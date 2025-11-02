FROM python:3-slim

RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY extract_flashcards.py .

RUN chmod u+x extract_flashcards.py

ENTRYPOINT ["python", "/app/extract_flashcards.py"]
