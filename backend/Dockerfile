FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir --upgrade "pip>=25.0" "setuptools>=83.0.0" "wheel>=0.46.2" \
 && pip uninstall -y pip setuptools wheel

COPY . .

RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --disabled-password --uid 10001 appuser && \
    chown -R appuser:appgroup /app

USER 10001

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:5000/health', timeout=3).status==200 else 1)"

CMD ["python", "app.py"]
