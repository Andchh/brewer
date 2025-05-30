from airflow.models import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sensors.external_task import ExternalTaskSensor
from datetime import datetime, timedelta
import os

with DAG(
    dag_id='create_gold_breweries',
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["spark", "gold", "breweries", "aggregation"],
    default_args={
        'retries': 2,
        'retry_delay': timedelta(minutes=1),
        'owner': 'airflow'
    }
) as dag:
    
    start = EmptyOperator(task_id='start')
    
    # Sensor para aguardar a conclusão da DAG da camada silver
    '''wait_for_silver = ExternalTaskSensor(
                    task_id='wait_for_silver',
                    external_dag_id='create_silver_breweries',
                    external_task_id='end',  # Espera pela tarefa 'end' da DAG silver
                    timeout=600,  # Timeout de 10 minutos
                    poke_interval=60,  # Verifica a cada 1 minuto
                    mode='reschedule',  # Libera o worker durante a espera
                    allowed_states=['success'],  # Só prossegue se a DAG silver for bem-sucedida
                    failed_states=['failed', 'skipped', 'upstream_failed'],
                    execution_delta=timedelta(minutes=0)  # Se a DAG silver for executada na mesma hora
                )'''
    
    # Job Spark para criar as agregações na camada gold
    spark_job = DockerOperator(
        task_id='create_gold_breweries',
        image='bitnami/spark:3.2.1',
        user = '0',
        command='spark-submit --master local[*] --driver-memory 1g --executor-memory 1g /opt/airflow/spark/app/create_gold_breweries.py',
        docker_url='tcp://docker-proxy:2375',
        network_mode='brewer_default',
        mounts=[
            {
                "source": "brewer_spark-app-scripts",
                "target": "/opt/airflow/spark/app",
                "type": "volume"
            },
            {
                "source": "brewer_datalake-volume",
                "target": "/opt/airflow/datalake",
                "type": "volume"
            }
        ],
        auto_remove="success",
        tmp_dir="/tmp",
        mount_tmp_dir=False,
        api_version='auto',
        tty=True,
        mem_limit='2g',
        environment={
            'PYSPARK_PYTHON': 'python3',
            'PYSPARK_DRIVER_PYTHON': 'python3'
        }
    )
    
    end = EmptyOperator(task_id='end')
    
    # Definição do fluxo de tarefas
    start >> spark_job >> end