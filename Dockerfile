FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9000

ENTRYPOINT ["python", "-m", "app.mcp_server"]
CMD ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9000"]
