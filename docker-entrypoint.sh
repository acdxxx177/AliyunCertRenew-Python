#!/bin/bash
set -e

echo "Starting cron daemon..."

# 检查 domains.yaml 配置文件是否存在
if [ ! -f "${DOMAINS_CONFIG_PATH:-/app/config/domains.yaml}" ]; then
    echo "Warning: Configuration file not found at ${DOMAINS_CONFIG_PATH:-/app/config/domains.yaml}"
    echo "Please mount your domains.yaml file to the container"
    echo "Example: -v /path/to/domains.yaml:/app/config/domains.yaml"
fi

# 启动 cron 守护进程
cron

# 保持容器运行，并显示日志
echo "Cron started. Logs will be written to /app/logs/cron.log"
echo "Current cron schedule: ${CRON_SCHEDULE:-0 2 */3 * *}"
echo "Config file path: ${DOMAINS_CONFIG_PATH:-/app/config/domains.yaml}"

# 实时显示日志文件
if [ -f /app/logs/cron.log ]; then
    tail -f /app/logs/cron.log
else
    # 等待日志文件创建
    while [ ! -f /app/logs/cron.log ]; do
        sleep 1
    done
    tail -f /app/logs/cron.log
fi
