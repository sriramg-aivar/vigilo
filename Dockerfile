FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY main.py .
COPY src/ src/

# Non-root user
RUN useradd -m vigilo
USER vigilo

ENTRYPOINT ["python3", "main.py"]
CMD ["scan", "--mock"]
