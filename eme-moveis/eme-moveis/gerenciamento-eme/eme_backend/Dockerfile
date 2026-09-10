# ============================================================
# Dockerfile — Backend EME Móveis (FastAPI)
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# Instala dependências Python primeiro (camada cacheável).
# As libs do requirements.txt já distribuem wheels pré-compiladas para
# linux/amd64 e linux/arm64, então nenhum compilador de sistema é necessário.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Usuário não-root por segurança
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck simples usando a rota raiz já existente em main.py
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
