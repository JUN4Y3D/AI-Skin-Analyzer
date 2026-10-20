FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TF_CPP_MIN_LOG_LEVEL=2 OMP_NUM_THREADS=2 TF_NUM_INTEROP_THREADS=2 TF_NUM_INTRAOP_THREADS=2
WORKDIR /srv
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app /srv/app
COPY server.py /srv/server.py
COPY private_artifacts/reports/private /srv/reports/private
EXPOSE 8080
CMD ["python", "server.py"]
