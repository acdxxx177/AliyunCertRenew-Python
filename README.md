# AliyunCertRenew

**基于 [AliyunCertRenew](https://github.com/lyc8503/AliyunCertRenew) 和[AliyunCertRenew-Python](https://github.com/wsgfz/AliyunCertRenew-Python/tree/main) 的 Python 移植版本，方便自行修改**  
**注意：环境变量名有改动**

本程序用于自动续期阿里云云上资源（如 CDN/函数计算）的免费 SSL 证书，支持定时任务自动执行。

---

## 目录

- [背景](#背景)
- [准备工作](#准备工作)
- [配置说明](#配置说明)
- [部署方式](#部署方式)
  - [方式一：Docker Compose 部署（推荐）](#方式一 docker-compose-部署推荐)
  - [方式二：Docker 部署](#方式二 docker-部署)
  - [方式三：本地部署](#方式三本地部署)
- [配置格式说明](#配置格式说明)
- [运行效果](#运行效果)
- [故障排查](#故障排查)
- [项目结构](#项目结构)

---

## 背景

[之前](https://help.aliyun.com/zh/ssl-certificate/product-overview/notice-on-adjustment-of-service-policies-for-free-certificates) 阿里云将个人免费证书的时长调整为了三个月。云上资源也无法使用 ACME 自动申请部署新证书，每三个月就需要手动登陆控制台续期，且只会在证书过期前一个月有短信提醒。操作繁琐之外，如果忘记续期还会导致意外的服务中断。

---

## 准备工作

请先确认以下内容：

1. ✅ 你的域名 DNS 解析已由阿里云托管（用以完成域名 DNS 认证）
2. ✅ 目前你已在阿里云上申请并部署 SSL 证书（程序会自动按照当前的配置续期）
3. ✅ 创建一个 [RAM 子用户](https://ram.console.aliyun.com/users)，授予 `AliyunYundunCertFullAccess` 权限，创建并保存一对 AccessKey ID 和 AccessKey Secret

---

## 配置说明

### 1. 配置文件 `domains.yaml`

复制示例配置：

```bash
cp domains.yaml.example domains.yaml
```

编辑 `domains.yaml`，配置你的域名：

```yaml
domains:
  # 云资源类型部署（推荐）
  - domain: "example.com"
    deploy_type: "cloud"
    resource_id: 256644

  # 服务器类型部署
  - domain: "api.example.com"
    deploy_type: "server"
    cert_path: "/etc/nginx/certs/mysite/"
    key_path: "/etc/nginx/certs/mysite/key.pem"
    reload_cmd: "nginx -s reload"
```

### 2. 环境变量

| 变量名                           | 必需 | 默认值                     | 说明                                             |
| -------------------------------- | ---- | -------------------------- | ------------------------------------------------ |
| `ALIYUN_ACCESS_KEY_ID_RENEW`     | ✅   | -                          | 阿里云 AccessKey ID                              |
| `ALIYUN_ACCESS_KEY_SECRET_RENEW` | ✅   | -                          | 阿里云 AccessKey Secret                          |
| `LOG_OUTPUT`                     | ❌   | `console`                  | 日志输出方式：`console` / `file` / `both`        |
| `LOG_LEVEL`                      | ❌   | `INFO`                     | 日志级别：`DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `CRON_SCHEDULE`                  | ❌   | `0 2 */3 * *`              | 定时任务执行时间（cron 表达式）                  |
| `DOMAINS_CONFIG_PATH`            | ❌   | `/app/config/domains.yaml` | 配置文件路径（Docker 内）                        |

---

## 部署方式

### 方式一：Docker Compose 部署（推荐）

#### 1. 准备文件

```bash
# 复制配置文件
cp domains.yaml.example domains.yaml
cp .env.example .env
```

#### 2. 编辑 `.env` 文件

```bash
ALIYUN_ACCESS_KEY_ID_RENEW=your_access_key_id
ALIYUN_ACCESS_KEY_SECRET_RENEW=your_access_key_secret
CRON_SCHEDULE=0 2 */3 * *
LOG_OUTPUT=file
```

#### 3. 编辑 `domains.yaml`

根据你的实际域名和资源配置。

#### 4. 构建并启动

```bash
docker-compose up -d
```

#### 5. 查看日志

```bash
docker-compose logs -f
```

#### 6. 停止/重启

```bash
docker-compose stop    # 停止
docker-compose start   # 启动
docker-compose restart # 重启
docker-compose down    # 停止并删除容器
```

---

### 方式二：Docker 部署

#### 1. 构建镜像

```bash
docker build -t aliyun-cert-renew .
```

#### 2. 运行容器

```bash
docker run -d \
  --name cert-renew \
  -e ALIYUN_ACCESS_KEY_ID_RENEW="your_access_key_id" \
  -e ALIYUN_ACCESS_KEY_SECRET_RENEW="your_access_key_secret" \
  -e CRON_SCHEDULE="0 2 */3 * *" \
  -e LOG_OUTPUT="file" \
  -v $(pwd)/domains.yaml:/app/config/domains.yaml:ro \
  -v $(pwd)/logs:/app/logs \
  aliyun-cert-renew
```

#### 3. 查看日志

```bash
# 查看容器日志
docker logs -f cert-renew

# 查看应用日志文件
cat logs/cron.log
```

#### 4. 更新配置

修改 `domains.yaml` 后重启容器：

```bash
docker restart cert-renew
```

---

### 方式三：本地部署

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 设置环境变量并运行

```bash
# 设置必需的环境变量
export ALIYUN_ACCESS_KEY_ID_RENEW="你的 AccessKey ID"
export ALIYUN_ACCESS_KEY_SECRET_RENEW="你的 AccessKey Secret"

# 可选：设置日志输出方式
export LOG_OUTPUT="file"

# 运行程序
python main.py
```

#### 3. 配置定时任务（可选）

使用 crontab 每 3 天执行一次：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每 3 天凌晨 2 点执行）
0 2 */3 * * cd /path/to/AliyunCertRenew && /usr/bin/python3 main.py
```

---

## 配置格式说明

### 云资源部署（Cloud）

适用于阿里云 CDN、SLB、函数计算等云资源：

```yaml
domains:
  - domain: "example.com"
    deploy_type: "cloud"
    resource_id: 256644 # 云资源 ID
```

### 服务器部署（Server）

适用于自有服务器，证书会保存到指定路径：

```yaml
domains:
  - domain: "api.example.com"
    deploy_type: "server"
    cert_path: "/etc/nginx/certs/api/" # 证书文件路径
    key_path: "/etc/nginx/certs/api/key.pem" # 私钥文件路径
    reload_cmd: "nginx -s reload" # 可选：重载服务命令
```

---

## 运行效果

一次正常的续期运行日志如下：

```
2025-02-11 14:30:25,123 - INFO - 阿里云证书续期工具启动...
2025-02-11 14:30:25,456 - INFO - 域名 example.com 需要证书续期
2025-02-11 14:30:25,789 - INFO - 已为域名 example.com 创建新的证书申请
2025-02-11 14:31:25,123 - INFO - 订单当前状态：CHECKING
2025-02-11 14:32:25,234 - INFO - 订单当前状态：CHECKING
2025-02-11 14:33:25,345 - INFO - 订单当前状态：CHECKING
2025-02-11 14:34:25,456 - INFO - 订单当前状态：ISSUED
2025-02-11 14:34:25,567 - INFO - 已为域名 example.com 创建新证书：14764653
2025-02-11 14:34:30,678 - INFO - 已创建部署任务：92612
2025-02-11 14:34:32,789 - INFO - 已提交部署任务：92612
```

续期和部署成功后，阿里云会给用户发送短信和邮件提醒。

---

## 故障排查

### 1. 查看容器日志

```bash
docker logs cert-renew
```

### 2. 进入容器检查

```bash
docker exec -it cert-renew /bin/bash

# 检查配置文件
cat /app/config/domains.yaml

# 手动运行测试
python main.py
```

### 3. 验证环境变量

```bash
docker exec cert-renew env | grep ALIYUN
```

### 4. 检查配置文件权限

```bash
docker exec cert-renew ls -la /app/config/domains.yaml
```

### 5. 查看应用日志

```bash
cat logs/cron.log
```

---

## 项目结构

```
AliyunCertRenew-Python/
├── main.py                 # 主程序文件
├── config_schema.py        # 配置模型定义
├── requirements.txt        # Python 依赖包
├── domains.yaml.example    # 配置文件示例
├── Dockerfile              # Docker 镜像配置
├── docker-compose.yml      # Docker Compose 配置
├── docker-entrypoint.sh    # 容器启动脚本
├── crontab                 # 定时任务配置
├── DOCKER_DEPLOY.md        # 详细 Docker 部署文档
├── README.md               # 项目说明
└── LICENSE                 # 许可证
```

---

## 安全建议

1. **不要将 AccessKey 提交到 Git**
   - 使用 `.env` 文件存储敏感信息
   - 将 `.env` 添加到 `.gitignore`

2. **限制 RAM 权限**
   - 只授予 `AliyunYundunCertFullAccess` 最小权限

3. **定期轮换 AccessKey**
   - 建议每 90 天更换一次

4. **使用只读挂载**
   - 配置文件使用 `:ro` 只读挂载，防止意外修改

---

## 许可证

MIT License
