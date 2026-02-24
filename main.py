import os
import yaml
import time
import logging
from config_schema import Config, DeployType
from typing import Optional
from alibabacloud_cas20200407.client import Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_cas20200407 import models as cas_models
from alibabacloud_tea_util import models as util_models


def is_expiring_soon(expire_time: int, days=10) -> bool:
    """计算时间，是否小于days
        expire_time 时间戳(秒)
    """
    if not expire_time:
        return False
    # days 天的总秒数
    threshold = days * 24 * 60 * 60
    current_time = int(time.time())
    
    # 如果 证书过期时间 - 当前时间 < 7天的秒数，说明快过期了
    return (expire_time - current_time) < threshold

def setup_logging():
    """配置日志"""
    # 从环境变量获取日志级别，默认为 INFO
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    level = getattr(logging, log_level, logging.INFO) 
    
    # 从环境变量获取日志输出配置，默认为console
    log_output = os.getenv('LOG_OUTPUT', 'console').lower()
    
    handlers = []
    
    if log_output == 'file':
        # 只输出到文件
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_filename = os.path.join(script_dir, f'aliyun_cert_renew_{timestamp}.log')
        handlers.append(logging.FileHandler(log_filename, encoding='utf-8'))
        print(f"日志将保存到文件: {log_filename}")
    elif log_output == 'both':
        # 同时输出到控制台和文件
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_filename = os.path.join(script_dir, f'aliyun_cert_renew_{timestamp}.log')
        handlers.append(logging.StreamHandler())
        handlers.append(logging.FileHandler(log_filename, encoding='utf-8'))
        print(f"日志将同时输出到控制台和文件: {log_filename}")
    else:
        # 默认只输出到控制台
        handlers.append(logging.StreamHandler())
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def create_client() -> Client:
    """创建阿里云客户端"""
    key_id = os.getenv('ALIYUN_ACCESS_KEY_ID_RENEW')
    key_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET_RENEW')
    
    if not key_id or not key_secret:
        raise ValueError("请设置 ALIYUN_ACCESS_KEY_ID_RENEW 和 ALIYUN_ACCESS_KEY_SECRET_RENEW 环境变量")
    
    config = open_api_models.Config(
        access_key_id=key_id,
        access_key_secret=key_secret,
        endpoint='cas.aliyuncs.com'
    )
    return Client(config)

def get_basic_info(client: Client) -> dict[str, cas_models.ListUserCertificateOrderResponseBodyCertificateOrderList]:
    """获取域名证书基本信息"""
    try:
        logging.info("获取账号下所有域名信息")
        request = cas_models.ListUserCertificateOrderRequest(order_type="CERT")
        cert_list = client.list_user_certificate_order_with_options(request, util_models.RuntimeOptions())

        # 创建容器，存储每个域名最新的证书
        domain_dict: dict[str, cas_models.ListUserCertificateOrderResponseBodyCertificateOrderList] = {}
        for certificate in cert_list.body.certificate_order_list:
            _domain = certificate.common_name
            # 有可能有多个一样的域名，取创建时间最新的
            if _domain in domain_dict:
                _old = domain_dict.get(_domain)
                # 如果当前证书的创建时间比已存储的更新，则替换
                if certificate.cert_start_time > _old.cert_start_time:
                    domain_dict[_domain] = certificate
            else:
                domain_dict[_domain] = certificate
        logging.info(f"一共找到{len(domain_dict)}个域名")
        return domain_dict
    except Exception as error:
        logging.error(error)

def apply_new_cert(client: Client, domain: str) -> Optional[int]:
    """申请新证书
    返回新证书 ID，如果失败返回 None
    """
    try:
        request = cas_models.CreateCertificateForPackageRequestRequest(
            domain=domain,
            product_code="digicert-free-1-free",
            validate_type="DNS"
        )

        response = client.create_certificate_for_package_request_with_options(
            request, util_models.RuntimeOptions()
        )
        order_id = response.body.order_id
        logging.info(f"已为 {domain} 创建新的证书申请 (Order ID: {order_id})")

        # 等待证书签发 (30 分钟，每次检查 1 分钟)
        for i in range(30):
            logging.info(f"等待证书签发... ({i+1}/30)")
            time.sleep(60)
            order_request = cas_models.ListUserCertificateOrderRequest(
                keyword=domain,
                order_type="CPACK"
            )
            order_response = client.list_user_certificate_order_with_options(
                order_request, util_models.RuntimeOptions()
            )

            for entry in order_response.body.certificate_order_list:
                if entry.order_id == order_id:
                    logging.info(f"订单当前状态：{entry.status}")
                    if entry.status == "ISSUED":
                        cert_request = cas_models.ListUserCertificateOrderRequest(
                            keyword=domain,
                            order_type="CERT"
                        )
                        cert_response = client.list_user_certificate_order_with_options(
                            cert_request, util_models.RuntimeOptions()
                        )

                        for cert_entry in cert_response.body.certificate_order_list:
                            if cert_entry.instance_id == entry.instance_id:
                                logging.info(f"证书签发成功，Certificate ID: {cert_entry.certificate_id}")
                                return cert_entry.certificate_id

                        logging.error("未找到证书")
                        return None

        logging.error("等待证书签发超时 (30 分钟)")
        return None
    except Exception as error:
        logging.error(f"申请证书失败：{error}")
        return None

def deploy_cert(client: Client, cert_id: int, resource_ids: int) -> None:
    """部署证书"""
    # 获取联系人信息
    contact_request = cas_models.ListContactRequest()
    contact_response = client.list_contact_with_options(
        contact_request, util_models.RuntimeOptions()
    )
    
    if not contact_response.body.contact_list:
        raise ValueError("未找到联系人")
    
    # 创建部署任务
    deploy_request = cas_models.CreateDeploymentJobRequest(
        name=f"aliyun-cert-renew-auto-{int(time.time())}",
        resource_ids=resource_ids,
        cert_ids=str(cert_id),
        contact_ids=str(contact_response.body.contact_list[0].contact_id),
        job_type="user"
    )
    
    deploy_response = client.create_deployment_job_with_options(
        deploy_request, util_models.RuntimeOptions()
    )
    job_id = deploy_response.body.job_id
    logging.info(f"已创建部署任务: {job_id}")
    
    # 提交部署任务
    time.sleep(2)
    update_request = cas_models.UpdateDeploymentJobStatusRequest(
        job_id=job_id,
        status="scheduling"
    )
    client.update_deployment_job_status_with_options(
        update_request, util_models.RuntimeOptions()
    )
    logging.info(f"已提交部署任务: {job_id}")

def get_certificate_detail(client: Client, cert_id: int) -> Optional[tuple[str, str]]:
    """获取域名证书的证书文件信息"""
    try:
        request = cas_models.GetUserCertificateDetailRequest(cert_id=cert_id, cert_filter=False)
        cert_detail = client.get_user_certificate_detail_with_options(request, util_models.RuntimeOptions())
        return cert_detail.body.cert, cert_detail.body.key
    except Exception as error:
        logging.error(f"获取证书详情失败：{error}")
        return None

def main():
    """主函数"""
    setup_logging()
    logging.info("阿里云证书续期工具启动...")

    # 创建阿里云客户端
    client = create_client()
    try:
        # 加载领域配置
        # 从环境变量读取配置文件路径，默认为 domains.yaml
        config_path = os.getenv("DOMAINS_CONFIG_PATH", "domains.yaml")
        logging.info(f"加载配置文件：{config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)
            config = Config(**raw_config)
    except Exception as error:
        logging.error("加载 yaml 文件错误，请查看 yaml 文件")
        logging.error(error)
        return
    # 获取所有域名信息
    all_domains = get_basic_info(client)
    
    for items in config.domains:
        logging.info(f"正在查询域名：{items.domain}")
        if not items.domain in all_domains:
            logging.info(f"域名:{items.domain}未找到")
            continue
        _domains_info = all_domains.get(items.domain)
        logging.info(f"域名：{items.domain}过期时间为:{_domains_info.end_date}")
        # 检查过期时间，如果小于10天就开始重新申请
        is_renew = is_expiring_soon(_domains_info.cert_end_time)
        if is_renew:
            logging.info("天数小于10天,需要重新申请")
            # 申请新证书
            new_cert_id = apply_new_cert(client, items.domain)
            if not new_cert_id:
                logging.error(f"申请证书失败，跳过域名 {items.domain}")
                continue
            logging.info(f"已为域名 {items.domain} 创建新证书: {new_cert_id}")
            # 根据类型，分别部署云平台，或者生成文件
            if items.deploy_type == DeployType.CLOUD:
                # 这里调用云平台 SDK，使用 item.resource_id
                logging.info(f"为域名：{items.domain}部署到云资源: {items.resource_id}")
                deploy_cert(client, new_cert_id, items.resource_id)
                logging.info("部署成功!")

            elif items.deploy_type == DeployType.SERVER:
                # 获取 cert 文件和 key 文件
                cert_result = get_certificate_detail(client, _domains_info.certificate_id)
                if not cert_result:
                    logging.error(f"获取域名 {items.domain} 证书详情失败，跳过")
                    continue
                cert, key = cert_result
                
                # 保存证书文件
                cert_path = items.cert_path
                key_path = items.key_path
                
                # 创建目录
                os.makedirs(os.path.dirname(cert_path), exist_ok=True)
                os.makedirs(os.path.dirname(key_path), exist_ok=True)
                
                logging.info(f"保存证书文件到：{cert_path}")
                with open(cert_path, "w", encoding="utf-8") as f:
                    f.write(cert)
                
                logging.info(f"保存私钥文件到：{key_path}")
                with open(key_path, "w", encoding="utf-8") as f:
                    f.write(key)
                
                # 如果配置了重启命令，则执行
                if items.reload_cmd:
                    logging.info(f"执行命令：{items.reload_cmd}")
                    os.system(items.reload_cmd)
                else:
                    logging.info("未配置重启命令，跳过执行")
        else:
            logging.info(f"域名 {items.domain} 不需要续期")

if __name__ == "__main__":
    main() 