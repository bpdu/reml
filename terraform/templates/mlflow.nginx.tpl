server {
    listen 80;
    server_name mlflow.reml.bpdu.ru;

    location / {
%{ for ip in ui_allowed_ips ~}
        allow ${ip};
%{ endfor ~}
        deny all;
        auth_basic "Restricted";
        auth_basic_user_file /etc/nginx/.htpasswd_reml;
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        client_max_body_size 500M;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    access_log /var/log/nginx/mlflow_access.log;
    error_log /var/log/nginx/mlflow_error.log;
}
