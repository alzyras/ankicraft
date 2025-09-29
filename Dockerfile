FROM python:3.13-slim

WORKDIR /app

# Install uv and generate lock file from pyproject.toml
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir uv && \
    uv pip compile pyproject.toml --output-file requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

COPY ankicraft/ ./ankicraft/
COPY start_server.sh /start_server.sh

RUN chmod +x /start_server.sh && \
    adduser --disabled-password --gecos '' appuser && \
    chown -R appuser /app
USER appuser

EXPOSE 8080
CMD ["/start_server.sh"]
