FROM python:3.11-slim

LABEL maintainer="ye1991xin@163.com"
LABEL description="Aliyun Certificate Renewal Tool"

# 设置工作目录
WORKDIR /app

# 安装 cron
RUN apt-get update && \
    apt-get install -y --no-install-recommends cron && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY main.py .
COPY config_schema.py .

# 创建日志目录和配置目录
RUN mkdir -p /app/logs /app/config

# 设置环境变量默认值
ENV LOG_OUTPUT=console
ENV LOG_LEVEL=INFO
ENV CRON_SCHEDULE="0 2 */3 * *"
ENV DOMAINS_CONFIG_PATH=/app/config/domains.yaml

# 复制 cron 配置文件
COPY crontab /etc/cron.d/cert-renew

# 设置 cron 文件权限
RUN chmod 0644 /etc/cron.d/cert-renew && \
    crontab /etc/cron.d/cert-renew

# 创建启动脚本
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 启动脚本
ENTRYPOINT ["docker-entrypoint.sh"]
