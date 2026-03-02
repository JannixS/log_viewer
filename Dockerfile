# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app.py .
COPY templates/ templates/

# Log files are mounted at runtime via a volume; create the default mount point
RUN mkdir -p logs

EXPOSE 5000

ENV FLASK_DEBUG=0

CMD ["python", "app.py"]
