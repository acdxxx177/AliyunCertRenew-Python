# AliyunCertRenew

**基于[AliyunCertRenew](https://github.com/lyc8503/AliyunCertRenew) 的 Python移植版本，方便自行修改**
**注意：环境变量名有改动**


本程序用于自动续期阿里云云上资源(如 CDN/函数计算)的免费 SSL 证书



## 背景

[之前](https://help.aliyun.com/zh/ssl-certificate/product-overview/notice-on-adjustment-of-service-policies-for-free-certificates)阿里云将个人免费证书的时长调整为了三个月.  
云上资源也无法使用 ACME 自动申请部署新证书, 每三个月就需要手动登陆控制台续期, 且只会在证书过期前一个月有短信提醒.  
操作繁琐之外, 如果忘记续期还会导致意外的服务中断.

## 准备工作

请先确认以下内容:
1. 你的域名 DNS 解析已由阿里云托管 (用以完成域名 DNS 认证)
2. 目前你已在阿里云上申请并部署 SSL 证书 (程序会自动按照当前的配置续期)
3. 创建一个 [RAM 子用户](https://ram.console.aliyun.com/users), 授予 `AliyunYundunCertFullAccess` 权限, 创建并保存一对 AccessKey ID 和 AccessKey Secret

## 部署

程序从环境变量读取所需参数, 必填参数如下:

1. `DOMAIN`: 需要证书续期的域名, 多个域名用英文逗号分隔
2. `ALIYUN_ACCESS_KEY_ID_RENEW`: 上面提到的子用户 AccessKey ID
3. `ALIYUN_ACCESS_KEY_SECRET_RENEW`: 上面提到的子用户 AccessKey Secret

可选参数有:
- `LOG_OUTPUT`: 控制日志输出方式
  - `console` (默认): 只在控制台显示日志
  - `file`: 只保存到时间戳命名的日志文件
  - `both`: 同时在控制台显示和保存到文件

程序会检查对应 `DOMAIN` 中所有的域名, 如果存在域名的证书过期时间在 7 天内, 则会申请新的免费证书, 部署替换当前证书.

## 本地部署运行

#### 安装依赖

首先确保你的系统已安装Python 3.7+，然后安装依赖包：

```bash
pip install -r requirements.txt
```

#### 运行程序

设置环境变量并运行：

```bash
# 设置必需的环境变量
export ALIYUN_ACCESS_KEY_ID_RENEW="你的AccessKey ID"
export ALIYUN_ACCESS_KEY_SECRET_RENEW="你的AccessKey Secret"
export DOMAIN="example.com,www.example.com"  # 多个域名用逗号分隔

# 可选：设置日志输出方式
export LOG_OUTPUT="file"  # 或 "console", "both"

# 运行程序
python main.py
```

可以使用 crontab 定期运行, 建议每三天执行一次：

```bash
# 编辑crontab
crontab -e

# 添加以下行（每3天运行一次）
0 2 */3 * * cd /path/to/AliyunCertRenew && /usr/bin/python3 main.py
```

## 效果

一次正常的续期运行日志如下, 续期和部署成功后, 阿里云均会给用户发送短信和邮件提醒:

```
2025-02-11 14:30:25,123 - INFO - 阿里云证书续期工具启动...
2025-02-11 14:30:25,124 - INFO - 需要检查的域名: ['example.com']
2025-02-11 14:30:25,124 - INFO - >>> 检查域名 example.com
2025-02-11 14:30:25,456 - INFO - 域名 example.com 需要证书续期
2025-02-11 14:30:25,789 - INFO - 已为域名 example.com 创建新的证书申请
2025-02-11 14:31:25,123 - INFO - 订单当前状态: CHECKING
2025-02-11 14:32:25,234 - INFO - 订单当前状态: CHECKING
2025-02-11 14:33:25,345 - INFO - 订单当前状态: CHECKING
2025-02-11 14:34:25,456 - INFO - 订单当前状态: ISSUED
2025-02-11 14:34:25,567 - INFO - 已为域名 example.com 创建新证书: 14764653
2025-02-11 14:34:30,678 - INFO - 已创建部署任务: 92612
2025-02-11 14:34:32,789 - INFO - 已提交部署任务: 92612
```

## 项目结构

```
AliyunCertRenew/
├── main.py              # 主程序文件
├── requirements.txt     # Python依赖包
├── README.md           # 项目说明
└── LICENSE             # 许可证
```
