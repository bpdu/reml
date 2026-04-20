[Unit]
Description=MLflow Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="PATH=/home/ubuntu/reml-env/bin"
ExecStart=/home/ubuntu/reml-env/bin/mlflow server --host 127.0.0.1 --port 5000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
