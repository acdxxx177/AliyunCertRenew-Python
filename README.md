# AliyunCertRenew

**基于 [AliyunCertRenew](https://github.com/lyc8503/AliyunCertRenew) 和 [AliyunCertRenew-Python](https://github.com/wsgfz/AliyunCertRenew-Python/tree/main) 的 Python 移植版本，方便自行修改**
**注意：环境变量名有改动**

本程序用于自动续期阿里云云上资源（如 CDN/函数计算）的免费 SSL 证书。容器运行完脚本后自动退出，定时任务由宿主机管理。

---

## 目录

- [背景](#背景)
- [准备工作](#准备工作)
- [配置说明](#配置说明)
- [部署方式](#部署方式)
  - [方式一：Docker Compose 部署（推荐）](#方式一 docker-compose-部署推荐)
  - [方式二：Docker 部署](#方式二 docker-部署)
  - [方式三：Shell 脚本部署（推荐用于服务器部署）](#方式三 shell-脚本部署推荐用于服务器部署)
  - [方式四：本地部署](#方式四本地部署)
- [配置格式说明](#配置格式说明)
- [定时任务配置](#定时任务配置)
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
LOG_OUTPUT=file
```

#### 3. 编辑 `domains.yaml`

根据你的实际域名和资源配置。

#### 4. 构建并启动

```bash
docker-compose up
```

> **注意**：容器运行完脚本后会自动退出，这是正常行为。如需定时执行，请在宿主机上配置 cron 或 systemd timer。

#### 5. 查看日志

```bash
docker-compose logs
```

#### 6. 重新运行

```bash
docker-compose up --force-recreate
```

#### 7. 在宿主机上配置定时任务

编辑宿主机的 crontab：

```bash
crontab -e
```

添加以下行（每 3 天凌晨 2 点执行）：

```bash
0 2 */3 * * cd /path/to/AliyunCertRenew-Python && docker-compose up --force-recreate
```

---

### 方式二：Docker 部署

#### 1. 构建镜像

```bash
docker build -t aliyun-cert-renew .
```

#### 2. 运行容器

```bash
docker run --rm \
  --name cert-renew \
  -e ALIYUN_ACCESS_KEY_ID_RENEW="your_access_key_id" \
  -e ALIYUN_ACCESS_KEY_SECRET_RENEW="your_access_key_secret" \
  -e LOG_OUTPUT="file" \
  -v $(pwd)/domains.yaml:/app/config/domains.yaml:ro \
  -v $(pwd)/logs:/app/logs \
  aliyun-cert-renew
```

> **注意**：
> - `--rm` 参数表示容器退出后自动删除容器实例
> - 容器运行完脚本后会自动退出，这是正常行为

#### 3. 查看日志

```bash
# 查看容器日志
docker logs cert-renew

# 查看应用日志文件
cat logs/aliyun_cert_renew_*.log
```

#### 4. 在宿主机上配置定时任务

编辑宿主机的 crontab：

```bash
crontab -e
```

添加以下行（每 3 天凌晨 2 点执行）：

```bash
0 2 */3 * * docker run --rm -e ALIYUN_ACCESS_KEY_ID_RENEW="your_access_key_id" -e ALIYUN_ACCESS_KEY_SECRET_RENEW="your_access_key_secret" -v /path/to/domains.yaml:/app/config/domains.yaml:ro -v /path/to/logs:/app/logs aliyun-cert-renew
```

---

### 方式三：Shell 脚本部署（推荐用于服务器部署）

如果你使用 `deploy_type: "server"` 将证书部署到自有服务器，可以使用 `renew_ssl.sh` 脚本。该脚本会自动检测证书是否更新，并在更新后重载 Nginx。

#### 1. 准备文件和目录

```bash
# 复制配置文件
cp domains.yaml.example domains.yaml

# 创建必要的目录
mkdir -p logs ssl
```

#### 2. 编辑 `renew_ssl.sh` 脚本

编辑 `renew_ssl.sh`，修改以下配置：

```bash
# 阿里云配置参数
ALIYUN_ID="your_access_key_id"
ALIYUN_SECRET="your_access_key_secret"

# 宿主机路径配置
CONFIG_PATH="/path/to/domains.yaml"      # domains.yaml 配置文件路径
LOG_PATH="/path/to/logs"                 # 日志目录路径
SSL_CERT_PATH="/path/to/ssl"             # 证书保存目录路径

# 目标容器名称
TARGET_CONTAINER="my_nginx"              # Nginx 容器名称

SSL_FILE="/path/to/ssl/www.pem"          # 用于检测变化的证书文件路径
```

#### 3. 编辑 `domains.yaml`

配置服务器部署类型：

```yaml
domains:
  - domain: "api.example.com"
    deploy_type: "server"
    cert_path: "/app/ssl/cert.pem"    # 容器内路径，证书将保存到这里
    key_path: "/app/ssl/key.pem"      # 容器内路径，私钥将保存到这里
    reload_cmd: ""                    # 容器内重载命令（可选）
```

> **注意**：`cert_path` 和 `key_path` 是容器内的路径，需要与 `SSL_CERT_PATH` 挂载点对应。

#### 4. 构建镜像（如果还没有构建）

```bash
docker build -t aliyun-cert-renew .
```

#### 5. 运行脚本

```bash
chmod +x renew_ssl.sh
./renew_ssl.sh
```

#### 6. 配置定时任务

编辑 crontab：

```bash
crontab -e
```

添加以下行（每 3 天凌晨 2 点执行）：

```bash
0 2 */3 * * /path/to/AliyunCertRenew-Python/renew_ssl.sh >> /path/to/logs/renew.log 2>&1
```

---

### 方式四：本地部署

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
0 2 */3 * * cd /path/to/AliyunCertRenew-Python && /usr/bin/python3 main.py
```

---

## 定时任务配置

### 方式一：使用 Crontab（推荐）

编辑 crontab：

```bash
crontab -e
```

#### Docker Compose 部署

```bash
# 每 3 天凌晨 2 点执行
0 2 */3 * * cd /path/to/AliyunCertRenew-Python && docker-compose up --force-recreate
```

#### Docker 部署

```bash
# 每 3 天凌晨 2 点执行
0 2 */3 * * docker run --rm -e ALIYUN_ACCESS_KEY_ID_RENEW="your_access_key_id" -e ALIYUN_ACCESS_KEY_SECRET_RENEW="your_access_key_secret" -v /path/to/domains.yaml:/app/config/domains.yaml:ro -v /path/to/logs:/app/logs aliyun-cert-renew
```

#### Shell 脚本部署

```bash
# 每 3 天凌晨 2 点执行
0 2 */3 * * /path/to/AliyunCertRenew-Python/renew_ssl.sh >> /path/to/logs/renew.log 2>&1
```

### 方式二：使用 systemd Timer（更现代的方式）

创建 service 文件 `/etc/systemd/system/cert-renew.service`：

```ini
[Unit]
Description=Aliyun Certificate Renewal
After=docker.service

[Service]
Type=oneshot
ExecStart=/path/to/AliyunCertRenew-Python/renew_ssl.sh
```

创建 timer 文件 `/etc/systemd/system/cert-renew.timer`：

```ini
[Unit]
Description=Run Aliyun Certificate Renewal every 3 days
Requires=cert-renew.service

[Timer]
OnBootSec=10min
OnUnitActiveSec=3d
Unit=cert-renew.service

[Install]
WantedBy=timers.target
```

启用并启动 timer：

```bash
sudo systemctl daemon-reload
sudo systemctl enable cert-renew.timer
sudo systemctl start cert-renew.timer
```

查看 timer 状态：

```bash
systemctl list-timers
systemctl status cert-renew.timer
```

### 方式三：使用项目提供的 crontab 文件

项目提供了 `crontab` 文件模板，可以复制并修改：

```bash
cp crontab /etc/cron.d/aliyun-cert-renew
```

编辑 `/etc/cron.d/aliyun-cert-renew`，设置正确的路径和 Cron 表达式。

---

## 配置格式说明

### 云资源部署（Cloud）

适用于阿里云 CDN、SLB、函数计算等云资源：

```yaml
domains:
  # 方式 1：自动获取资源 ID（推荐）
  - domain: "example.com"
    deploy_type: "cloud"
    # 不配置 resource_id 时会自动获取域名关联的云产品资源 ID

  # 方式 2：手动指定资源 ID
  - domain: "www.example.com"
    deploy_type: "cloud"
    resource_id: 256644 # 可选，手动指定云资源 ID，多个用半角逗号（,）分隔
```

> **说明**：`resource_id` 字段可选。如果不配置，程序会自动获取域名关联的云产品资源 ID；如果找不到关联的资源 ID，会跳过部署。

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
docker run --rm -it --entrypoint /bin/bash aliyun-cert-renew

# 检查配置文件
cat /app/config/domains.yaml

# 手动运行测试
python main.py
```

### 3. 验证环境变量

```bash
docker run --rm -e ALIYUN_ACCESS_KEY_ID_RENEW="xxx" aliyun-cert-renew env | grep ALIYUN
```

### 4. 检查配置文件权限

```bash
docker run --rm -v $(pwd)/domains.yaml:/app/config/domains.yaml:ro aliyun-cert-renew ls -la /app/config/domains.yaml
```

### 5. 查看应用日志

```bash
cat logs/aliyun_cert_renew_*.log
```

---

## 项目结构

```
AliyunCertRenew-Python/
├── main.py                 # 主程序文件
├── config_schema.py        # 配置模型定义
├── requirements.txt        # Python 依赖包
├── domains.yaml.example    # 配置文件示例
├── crontab                 # Crontab 模板文件
├── renew_ssl.sh            # Shell 脚本（用于服务器部署）
├── Dockerfile              # Docker 镜像配置
├── docker-compose.yml      # Docker Compose 配置
├── docker-entrypoint.sh    # 容器启动脚本
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
