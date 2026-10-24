FROM python:3.11-slim 

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

CMD ["python", "app.py"]
