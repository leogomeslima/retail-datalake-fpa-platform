FROM apache/airflow:2.8.0-python3.11

USER airflow
COPY requirements-airflow.txt /tmp/requirements-airflow.txt
RUN pip install --no-cache-dir -r /tmp/requirements-airflow.txt

WORKDIR /opt/airflow/retail
ENV PYTHONPATH=/opt/airflow/retail
