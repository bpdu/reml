services:
  clickhouse:
    image: clickhouse/clickhouse-server:24.3
    container_name: clickhouse-server
    restart: unless-stopped
    ports:
      - "127.0.0.1:8123:8123"
      - "127.0.0.1:9000:9000"
    environment:
      CLICKHOUSE_DB: ${clickhouse_db}
      CLICKHOUSE_USER: ${clickhouse_user}
      CLICKHOUSE_PASSWORD: ${clickhouse_password}
      CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT: "1"
    volumes:
      - clickhouse-data:/var/lib/clickhouse
    mem_limit: 1200m
    cpus: 1.5

volumes:
  clickhouse-data:
