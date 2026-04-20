[Unit]
Description=Prefect Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="PATH=/home/ubuntu/reml-env/bin"
ExecStart=/home/ubuntu/reml-env/bin/prefect server start --host 127.0.0.1 --port 4200
Restart=always

[Install]
WantedBy=multi-user.target
