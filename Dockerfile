FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
COPY wheels/ /wheels/

ARG PIP_INSTALL_MODE=online
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_EXTRA_ARGS="--retries 10 --timeout 120"
RUN if [ "$PIP_INSTALL_MODE" = "offline" ]; then \
        python -m pip install --no-index --find-links /wheels -r requirements.txt; \
    else \
        python -m pip install $PIP_EXTRA_ARGS -r requirements.txt -i "$PIP_INDEX_URL"; \
    fi

COPY . .

EXPOSE 8881

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8881", "--workers", "1"]
