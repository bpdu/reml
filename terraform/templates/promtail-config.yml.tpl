server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yml

clients:
  - url: ${loki_push_url}

scrape_configs:
  - job_name: nginx
    static_configs:
      - targets:
          - localhost
        labels:
          job: nginx
          project: reml
          environment: ${environment}
          host: reml-controller
          __path__: /var/log/nginx/*.log

  - job_name: prefect
    static_configs:
      - targets:
          - localhost
        labels:
          job: prefect
          project: reml
          environment: ${environment}
          host: reml-controller
          __path__: /var/log/prefect/*.log

  - job_name: mlflow
    static_configs:
      - targets:
          - localhost
        labels:
          job: mlflow
          project: reml
          environment: ${environment}
          host: reml-controller
          __path__: /var/log/mlflow/*.log
