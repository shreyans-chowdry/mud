FROM python:3.12.10-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY backend/requirements.lock /app/backend/requirements.lock
RUN pip install --no-cache-dir -r /app/backend/requirements.lock
COPY backend /app/backend
COPY abi /app/abi
COPY config /app/config
COPY scripts/generate_merkle_tree.py scripts/verify_merkle_tree.py /app/scripts/
COPY deployments /app/deployments
RUN pip install --no-deps /app/backend && useradd --uid 10001 --create-home mud && chown -R mud:mud /app
USER mud
WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
