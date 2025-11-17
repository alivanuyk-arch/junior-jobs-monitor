from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import json

def airflow_vacancies_etl():
    """Задача ETL для вакансий"""
    # Здесь будет вызов функций из junior_jobs_monitor.py
    print("Airflow: Запуск ETL вакансий")
    return []

def airflow_news_etl():
    """Задача ETL для новостей"""
    print("Airflow: Запуск ETL новостей")
    return []

default_args = {
    'owner': 'data_engineer',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'junior_jobs_monitoring',
    default_args=default_args,
    description='Production ETL pipeline for Junior Data Engineer jobs',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['data_engineering', 'jobs'],
) as dag:
    
    vacancies_task = PythonOperator(
        task_id='extract_transform_vacancies',
        python_callable=airflow_vacancies_etl,
    )
    
    news_task = PythonOperator(
        task_id='extract_transform_news',
        python_callable=airflow_news_etl,
    )
