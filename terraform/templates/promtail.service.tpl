[Unit]
Description=Promtail Log Shipper
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/promtail -config.file=/etc/promtail/config.yml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
