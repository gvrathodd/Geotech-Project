# Container for Google Cloud Run (no Streamlit Cloud branding).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# Cloud Run sets $PORT (8080 by default)
CMD streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 \
    --server.headless=true --browser.gatherUsageStats=false
