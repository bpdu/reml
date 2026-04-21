[Unit]
Description=MLflow Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="PATH=/home/ubuntu/reml-env/bin"
Environment="MLFLOW_SERVER_ALLOWED_HOSTS=mlflow.reml.bpdu.ru,127.0.0.1,localhost"
Environment="MLFLOW_SERVER_CORS_ALLOWED_ORIGINS=https://mlflow.reml.bpdu.ru"
ExecStart=/home/ubuntu/reml-env/bin/mlflow server --host 127.0.0.1 --port 5000 --workers 2 --default-artifact-root /home/ubuntu/mlflow_artifacts
Restart=always

[Install]
WantedBy=multi-user.target
