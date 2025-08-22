import os
import time
import logging
from typing import List, Tuple, Optional
from alibabacloud_cas20200407.client import Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_cas20200407 import models as cas_models
from alibabacloud_tea_util import models as util_models

# 常量定义
RENEW_THRESHOLD = 7 * 86400 # 7天的秒数

def setup_logging():
    """配置日志"""
    level = logging.DEBUG 
    
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

def get_basic_info(client: Client, domain: str) -> Tuple[bool, List[dict]]:
    """获取域名证书基本信息"""
    request = cas_models.ListCloudResourcesRequest(keyword=domain)
    response = client.list_cloud_resources_with_options(request, util_models.RuntimeOptions())
    
    results = []
    need_renew = False
    
    for entry in response.body.data:
        if entry.domain == domain and entry.enable_https > 0:
            end_time = int(entry.cert_end_time) // 1000  # 转换为秒
            expire_time = end_time - int(time.time())
            logging.debug(f"证书 {entry.cert_id} (域名 {domain}) 将在 {expire_time} 秒后过期")
            
            if expire_time < RENEW_THRESHOLD:
                need_renew = True
            results.append(entry)
    
    if not results:
        raise ValueError(f"未找到域名 {domain} 的资源")
        
    return need_renew, results

def apply_new_cert(client: Client, domain: str) -> int:
    """申请新证书"""
    request = cas_models.CreateCertificateForPackageRequestRequest(
        domain=domain,
        product_code="digicert-free-1-free",
        validate_type="DNS"
    )
    
    response = client.create_certificate_for_package_request_with_options(
        request, util_models.RuntimeOptions()
    )
    order_id = response.body.order_id
    logging.info(f"已为 {domain} 创建新的证书申请")
    
    # 等待证书签发
    for _ in range(30):
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
                logging.info(f"订单当前状态: {entry.status}")
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
                            return cert_entry.certificate_id
                    
                    raise ValueError("未找到证书")
    
    raise TimeoutError("等待证书签发超时")

def deploy_cert(client: Client, cert_id: int, resource_ids: List[int]) -> None:
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
        resource_ids=",".join(str(rid) for rid in resource_ids),
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

def main():
    """主函数"""
    setup_logging()
    logging.info("阿里云证书续期工具启动...")
    
    # 创建两个不同的客户端
    resource_client =  create_client() # 用于资源操作的客户端
    cert_client = create_client()  # 用于证书操作的客户端
    
    domain_env = os.getenv('DOMAIN', '')
    if not domain_env:
        logging.fatal("未指定域名，退出...")
        return
    
    domains = domain_env.split(',')
    
    logging.info(f"需要检查的域名: {domains}")
    
    for domain in domains:
        logging.info(f">>> 检查域名 {domain}")
        try:
            # 使用资源账号检查证书状态
            need_renew, resources = get_basic_info(resource_client, domain)
            
            if not need_renew:
                logging.info(f"域名 {domain} 不需要续期")
                continue
                
            logging.info(f"域名 {domain} 需要证书续期")
            # 使用证书账号申请新证书
            new_cert_id = apply_new_cert(cert_client, domain)
            logging.info(f"已为域名 {domain} 创建新证书: {new_cert_id}")
            
            resource_ids = [res.id for res in resources]
            # 使用资源账号部署证书
            deploy_cert(resource_client, new_cert_id, resource_ids)
            
        except Exception as e:
            logging.error(f"处理域名 {domain} 时发生错误: {str(e)}")
            continue

if __name__ == "__main__":
    main() 