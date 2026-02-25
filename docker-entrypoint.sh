#!/bin/bash
set -e

# 检查 domains.yaml 配置文件是否存在
if [ ! -f "${DOMAINS_CONFIG_PATH:-/app/config/domains.yaml}" ]; then
    echo "Warning: Configuration file not found at ${DOMAINS_CONFIG_PATH:-/app/config/domains.yaml}"
    echo "Please mount your domains.yaml file to the container"
    echo "Example: -v /path/to/domains.yaml:/app/config/domains.yaml"
fi

echo "Starting Aliyun Certificate Renewal..."
echo "Config file path: ${DOMAINS_CONFIG_PATH:-/app/config/domains.yaml}"
echo "Log output: ${LOG_OUTPUT:-console}"
echo "Log level: ${LOG_LEVEL:-INFO}"

# 运行主程序
python main.py

echo "Certificate renewal completed."
