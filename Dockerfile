FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir build && python -m build --wheel && pip wheel --no-cache-dir dist/*.whl -w /wheels

FROM python:3.11-slim AS runtime

RUN useradd --create-home --uid 10001 rada
WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

COPY configs ./configs
COPY scripts ./scripts
COPY migrations ./migrations

USER rada
ENV RADA_DATA_STORE_MODE=sqlite \
    RADA_SQLITE_URL=sqlite:////app/data/rada.db \
    RADA_AUDIT_DB_PATH=/app/data/rada_audit.db \
    RADA_FEEDBACK_DB_PATH=/app/data/rada_feedback.db

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "rada.main:app", "--host", "0.0.0.0", "--port", "8000"]
