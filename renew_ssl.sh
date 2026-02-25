#!/bin/bash

# =================================================================
# 脚本名称: renew_ssl.sh
# 描述: 自动续签阿里云 SSL 证书并重载 Nginx 配置
# =================================================================

# --- 阿里云配置参数 ---
ALIYUN_ID="xxxxxxx"
ALIYUN_SECRET="xxxxxx"

# 宿主机路径配置
CONFIG_PATH="/home/root/aliyun-renew/domains.yaml"
LOG_PATH="/home/root/aliyun-renew/logs"
SSL_CERT_PATH="/home/root/mywork/ssl"

# 目标容器名称
TARGET_CONTAINER="my_nginx"

SSL_FILE="/home/root/mywork/ssl/www.pem" # 替换为你证书路径中的任意一个文件(用来比对文件是否修改)

# --- 逻辑开始 ---

echo "[$(date +'%Y-%m-%d %H:%M:%S')] 开始确续签流程..."

# 1. 记录运行前的修改时间（如果没有文件则默认为0）
if [ -f "$SSL_FILE" ]; then
    BEFORE_TIME=$(stat -c %Y "$SSL_FILE")
else
    BEFORE_TIME=0
fi

# 2. 运行证书续签容器
# --rm 运行完自动删除容器，保持系统干净
docker run --rm \
  --name cert-renew-task \
  -e ALIYUN_ACCESS_KEY_ID_RENEW="$ALIYUN_ID" \
  -e ALIYUN_ACCESS_KEY_SECRET_RENEW="$ALIYUN_SECRET" \
  -e LOG_OUTPUT="console" \
  -v "$CONFIG_PATH":/app/config/domains.yaml:ro \
  -v "$LOG_PATH":/app/logs \
  -v "$SSL_CERT_PATH":/app/ssl \
  aliyun-cert-renew

# 3. 检查运行后的修改时间
if [ -f "$SSL_FILE" ]; then
    AFTER_TIME=$(stat -c %Y "$SSL_FILE")
else
    AFTER_TIME=0
fi

# 4. 对比时间戳
if [ "$BEFORE_TIME" != "$AFTER_TIME" ]; then
    echo "[$(date)] 检测到证书已更新，正在重载 Nginx..."
    docker exec "$TARGET_CONTAINER" nginx -s reload
else
    echo "[$(date)] 证书尚未过期或未发生变化，无需重载。"
fi

echo "[$(date +'%Y-%m-%d %H:%M:%S')] 任务全部完成。"