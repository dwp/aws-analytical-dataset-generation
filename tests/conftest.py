import os
import signal
import subprocess

import pytest
from pyspark.sql import SparkSession

TESTING = 'testing'


@pytest.fixture(scope='session')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = TESTING
    os.environ['AWS_SECRET_ACCESS_KEY'] = TESTING
    os.environ['AWS_SECURITY_TOKEN'] = TESTING
    os.environ['AWS_SESSION_TOKEN'] = TESTING


@pytest.fixture(autouse=True, scope='session')
def handle_server():
    print("Starting Moto Server")
    process = subprocess.Popen("moto_server s3",
                               stdout=subprocess.PIPE,
                               shell=True,
                               preexec_fn=os.setsid)
    yield
    print("Stopping Moto Server")
    os.killpg(os.getpgid(process.pid), signal.SIGTERM)


@pytest.fixture(scope='session')
def spark():
    os.environ["PYSPARK_SUBMIT_ARGS"] = (
        '--packages "org.apache.hadoop:hadoop-aws:2.7.3" --conf spark.jars.ivySettings=/root/ivysettings.xml pyspark-shell'
    )

    os.environ["PYSPARK_PYTHON"] = ('python3')
    os.environ["PYSPARK_DRIVER_PYTHON"] = ('python3')
    spark = (
        SparkSession.builder.master("local")
            .appName("adg-test")
            .config("spark.local.dir", "spark-temp")
            .enableHiveSupport()
            .getOrCreate()
    )

    # Setup spark to use s3, and point it to the moto server.
    hadoop_conf = spark.sparkContext._jsc.hadoopConfiguration()
    hadoop_conf.set("fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    hadoop_conf.set("fs.s3a.access.key", "mock")
    hadoop_conf.set("fs.s3a.secret.key", "mock")
    hadoop_conf.set("fs.s3a.endpoint", "http://127.0.0.1:5000")

    spark.sql("create database if not exists test_db")
    yield spark
    print("Stopping Spark")
    spark.stop()
