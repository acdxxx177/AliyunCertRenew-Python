FROM python:3.11-slim

LABEL maintainer="ye1991xin@163.com"
LABEL description="Aliyun Certificate Renewal Tool"

# 设置工作目录
WORKDIR /app

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
ENV DOMAINS_CONFIG_PATH=/app/config/domains.yaml

# 直接运行主程序
CMD ["python", "main.py"]
