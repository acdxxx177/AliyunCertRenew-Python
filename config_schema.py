from enum import Enum
from typing import List, Union, Optional
from pydantic import BaseModel, Field

class DeployType(str, Enum):
    CLOUD = "cloud"      # 云资源部署
    SERVER = "server"    # 本地服务器部署

class BaseDomainConfig(BaseModel):
    domain: str

class CloudDeployConfig(BaseDomainConfig):
    deploy_type: DeployType = DeployType.CLOUD
    resource_id: int = Field(..., description="云资源 ID，必须为整数")  # 云资源 ID (如 CDN/SLB 实例 ID)

class ServerDeployConfig(BaseDomainConfig):
    deploy_type: DeployType = DeployType.SERVER
    cert_path: str       # 证书存放路径
    key_path: str       # key证书存放路径
    reload_cmd: Optional[str] = None     # 部署后重启服务的命令，如 "nginx -s reload"

# 最终的配置容器
class Config(BaseModel):
    domains: List[Union[CloudDeployConfig, ServerDeployConfig]]