from typing import List, Optional, Union
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 项目信息
    # PROJECT_NAME: 项目名称，用于API文档标题等
    # 建议配置范围: 任意有效字符串
    # 调整考虑因素: 更改项目名称会影响API文档显示和日志标识
    PROJECT_NAME: str = "OpenServerHub"
    
    # VERSION: 项目版本号，用于API文档版本标识
    # 建议配置范围: 符合语义化版本规范的字符串 (如 "1.0.0")
    # 调整考虑因素: 版本变更应遵循语义化版本规范，影响API文档和客户端兼容性
    VERSION: str = "1.0.0"
    
    # VENDOR_NAME: 厂商名称
    # 建议配置范围: 有效的字符串
    # 调整考虑因素: 用于产品信息页面显示
    VENDOR_NAME: str = "opensource"
    
    # VENDOR_URL: 厂商URL
    # 建议配置范围: 有效的URL
    # 调整考虑因素: 用于产品信息页面链接
    VENDOR_URL: str = "https://github.com/zha0jf/OpenServerHub"
    
    # ENVIRONMENT: 运行环境标识，用于区分开发、测试、生产环境
    # 建议配置范围: "development", "testing", "production"
    # 调整考虑因素: 不同环境可能启用不同的安全措施、日志级别和调试功能
    ENVIRONMENT: str = "development"  # 添加环境变量，默认为开发环境
    
    # API_V1_STR: API v1版本的基础路径
    # 建议配置范围: 以"/"开头的有效URL路径
    # 调整考虑因素: 更改会影响所有API端点的访问路径，需要同步更新前端和服务调用
    API_V1_STR: str = "/api/v1"
    
    # 数据库配置 (开发阶段使用SQLite)
    # 统一使用与Docker Compose一致的路径
    
    # DATABASE_URL: 数据库连接字符串
    # 建议配置范围: 有效的数据库URL (如 SQLite: "sqlite:///./data/openserverhub.db", MySQL: "mysql://user:pass@host:port/db")
    # 调整考虑因素: 更改数据库类型需要相应调整连接参数；生产环境应使用更安全的数据库如PostgreSQL或MySQL
    DATABASE_URL: str = "sqlite:///./data/openserverhub.db"
    
    # DATABASE_POOL_SIZE: 数据库连接池大小，控制同时打开的数据库连接数
    # 建议配置范围: 30 (基础连接数)
    # 调整考虑因素: 数据库连接池大小应与定时任务并发数协调，建议值为定时任务并发数的2-3倍
    # 注意：SQLite在异步模式下使用NullPool，不支持设置连接池参数，此配置仅适用于MySQL/PostgreSQL
    DATABASE_POOL_SIZE: int = 30  # 数据库连接池大小
    
    # DATABASE_MAX_OVERFLOW: 数据库连接池最大溢出连接数，超过池大小后允许创建的额外连接数
    # 建议配置范围: 40 (最大溢出连接数)
    # 调整考虑因素: 溢出连接数应为池大小的1.3-1.5倍，以应对突发流量
    # 注意：SQLite在异步模式下使用NullPool，不支持设置连接池参数，此配置仅适用于MySQL/PostgreSQL
    DATABASE_MAX_OVERFLOW: int = 40  # 数据库连接池最大溢出连接数
    
    # DATABASE_POOL_RECYCLE: 数据库连接回收时间(秒)，防止连接因长时间空闲而失效
    # 建议配置范围: 300-7200 (5分钟到2小时)
    # 调整考虑因素: 过短会频繁重建连接增加开销，过长可能导致连接失效
    DATABASE_POOL_RECYCLE: int = 3600  # 数据库连接回收时间(秒)
    
    # DATABASE_POOL_PRE_PING: 数据库连接前检测有效性，确保获取的连接可用
    # 建议配置范围: True/False
    # 调整考虑因素: 开启会增加少量开销但提高稳定性，关闭可减少开销但可能遇到失效连接
    DATABASE_POOL_PRE_PING: bool = True  # 数据库连接前检测有效性
    
    # DATABASE_ECHO: 是否显示SQL语句，用于调试
    # 建议配置范围: False (生产环境), True (开发环境)
    # 调整考虑因素: 开启有助于调试但会产生大量日志输出，生产环境建议关闭
    DATABASE_ECHO: bool = False  # 是否显示SQL语句(开发环境可设为True)
    
    # 安全配置
    
    # SECRET_KEY: JWT加密密钥，用于生成和验证访问令牌
    # 建议配置范围: 强随机字符串，至少32字符
    # 调整考虑因素: 必须保密，泄露会导致所有令牌失效；生产环境必须更换默认值
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    
    # ACCESS_TOKEN_EXPIRE_MINUTES: 访问令牌有效期(分钟)
    # 建议配置范围: 30-43200 (30分钟到30天)
    # 调整考虑因素: 过短影响用户体验，过长增加安全风险；需平衡安全性和便利性
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8天
    
    # ALGORITHM: JWT签名算法
    # 建议配置范围: HS256, RS256等标准JWT算法
    # 调整考虑因素: 更改算法需要同步更新密钥格式；HS256使用对称密钥，RS256使用非对称密钥
    ALGORITHM: str = "HS256"
    
    # CORS配置 - 支持字符串和列表两种格式
    # BACKEND_CORS_ORIGINS: 允许跨域访问的源列表
    # 建议配置范围: 前端应用的实际部署地址列表
    # 调整考虑因素: 过于宽松会带来安全风险，过于严格会导致前端无法访问API；生产环境应明确指定域名
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",  # React前端
        "http://127.0.0.1:3000",
    ]
    
    # 日志配置
    
    # LOG_LEVEL: 日志级别
    # 建议配置范围: DEBUG, INFO, WARNING, ERROR, CRITICAL
    # 调整考虑因素: DEBUG产生详细日志适合开发调试，INFO适合生产环境；级别越低日志量越大
    LOG_LEVEL: str = "DEBUG" if os.getenv("DEBUG", "").lower() == "true" else "INFO"
    
    # LOG_FILE: 日志文件路径
    # 建议配置范围: 有效的文件路径，确保目录存在且有写权限
    # 调整考虑因素: 需确保目录存在且有写权限；日志文件会持续增长，需配置轮转策略
    LOG_FILE: str = "logs/app.log"
    
    # IPMI配置
    
    # IPMI_TIMEOUT: IPMI操作超时时间(秒)
    # 建议配置范围: 5-30 (根据网络状况调整)
    # 调整考虑因素: 过短可能导致正常操作超时失败，过长会阻塞其他操作
    IPMI_TIMEOUT: int = 10  # 进一步降低超时时间到10秒
    
    # IPMI_CONCURRENT_LIMIT: IPMI并发操作限制
    # 建议配置范围: 25 (IPMI并发操作限制)
    # 调整考虑因素: 并发限制应与数据库连接池协调，避免数据库成为瓶颈
    IPMI_CONCURRENT_LIMIT: int = 25  # IPMI并发限制
    
    # IPMI_THREAD_POOL_SIZE: IPMI线程池大小，用于处理Redfish等异步操作
    # 建议配置范围: 30 (IPMI线程池大小)
    # 调整考虑因素: 线程池大小应根据并发需求调整，Redfish等IO密集型操作可适当增加线程数
    IPMI_THREAD_POOL_SIZE: int = 30  # IPMI线程池大小
    
    # IPMI_PROCESS_POOL_SIZE: IPMI进程池大小，用于处理pyghmi等阻塞操作
    # 建议配置范围: 6 (IPMI进程池大小)
    # 调整考虑因素: 进程池大小应根据CPU核心数调整，适当增加可提高并发处理能力
    IPMI_PROCESS_POOL_SIZE: int = 6  # IPMI进程池大小
    
    # IPMI_DEFAULT_PORT: IPMI默认端口号
    # 建议配置范围: 623 (标准IPMI端口)
    # 调整考虑因素: 更改为非标准端口需确保所有服务器配置一致
    IPMI_DEFAULT_PORT: int = 623  # IPMI默认端口
    
    # IPMI_PRIVILEGE_LEVEL: IPMI权限级别
    # 建议配置范围: 1-15 (根据服务器厂商实现)
    # 调整考虑因素: 过高级别可能带来安全风险，过低可能无法执行某些操作
    IPMI_PRIVILEGE_LEVEL: int = 4  # IPMI权限级别
    
    # IPMI_INTERFACE_TYPE: IPMI接口类型
    # 建议配置范围: "lan", "lanplus" (推荐使用lanplus以获得更好安全性)
    # 调整考虑因素: lan适用于简单网络环境，lanplus支持加密传输更安全
    IPMI_INTERFACE_TYPE: str = "lanplus"  # IPMI接口类型
    
    # IPMI Exporter配置
    
    # IPMI_EXPORTER_URL: IPMI Exporter服务地址
    # 建议配置范围: 有效的HTTP(S) URL，指向IPMI Exporter服务
    # 调整考虑因素: 需与Docker Compose配置一致；HTTPS提供更好的安全性
    IPMI_EXPORTER_URL: str = "http://ipmi-exporter:9290"  # IPMI Exporter服务地址
    
    # IPMI_EXPORTER_MODULE: IPMI Exporter模块
    # 建议配置范围: "remote" (标准模块)
    # 调整考虑因素: 除非有特殊定制需求，否则使用默认值
    IPMI_EXPORTER_MODULE: str = "remote"  # IPMI Exporter模块
    
    # IPMI_EXPORTER_TIMEOUT: IPMI Exporter超时时间(毫秒)
    # 建议配置范围: 10000-60000 (10-60秒)
    # 调整考虑因素: 过短可能导致监控数据采集失败，过长会延迟告警响应
    IPMI_EXPORTER_TIMEOUT: int = 30000  # IPMI Exporter超时时间(毫秒)
    
    # IPMI操作超时配置
    
    # IPMI_POWER_STATE_TIMEOUT: 获取电源状态超时时间(秒)
    # 建议配置范围: 10-30
    # 调整考虑因素: 电源状态查询相对较快，超时时间不宜过长
    IPMI_POWER_STATE_TIMEOUT: int = 15  # 获取电源状态超时时间(秒)
    
    # IPMI_POWER_CONTROL_TIMEOUT: 电源控制操作超时时间(秒)
    # 建议配置范围: 15-30
    # 调整考虑因素: 重启等操作可能需要更长时间完成
    IPMI_POWER_CONTROL_TIMEOUT: int = 20  # 电源控制操作超时时间(秒)
    
    # IPMI_SYSTEM_INFO_TIMEOUT: 获取系统信息超时时间(秒)
    # 建议配置范围: 20-60
    # 调整考虑因素: 系统信息包含多个查询，需要足够时间完成
    IPMI_SYSTEM_INFO_TIMEOUT: int = 30  # 获取系统信息超时时间(秒)
    
    # IPMI_SENSOR_DATA_TIMEOUT: 获取传感器数据超时时间(秒)
    # 建议配置范围: 30-120
    # 调整考虑因素: 传感器数据量大，查询时间较长，需给予充足时间
    IPMI_SENSOR_DATA_TIMEOUT: int = 45  # 获取传感器数据超时时间(秒)
    
    # Redfish配置
    
    # REDFISH_TIMEOUT: Redfish请求超时时间(秒)
    # 建议配置范围: 10-30
    # 调整考虑因素: Redfish基于HTTP协议，通常响应较快，超时时间不宜过长
    REDFISH_TIMEOUT: int = 15  # Redfish请求超时时间(秒)
    
    # REDFISH_VERIFY_SSL: Redfish SSL证书验证
    # 建议配置范围: True (生产环境), False (测试环境)
    # 调整考虑因素: 关闭验证会带来安全风险，但在测试环境中可以绕过自签名证书问题
    REDFISH_VERIFY_SSL: bool = False  # Redfish SSL证书验证
    
    # 定时任务配置
    
    # POWER_STATE_REFRESH_INTERVAL: 电源状态刷新间隔（分钟）
    # 建议配置范围: 1-60 (根据实时性要求调整)
    # 调整考虑因素: 过短会增加服务器负载和网络流量，过长可能导致状态更新不及时
    POWER_STATE_REFRESH_INTERVAL: int = 3  # 电源状态刷新间隔（分钟）
    
    # POWER_STATE_REFRESH_ENABLED: 是否启用自动刷新
    # 建议配置范围: True/False
    # 调整考虑因素: 关闭后需手动刷新服务器状态，开启会占用一定系统资源
    POWER_STATE_REFRESH_ENABLED: bool = True  # 是否启用自动刷新
    
    # SCHEDULER_CONCURRENCY_LIMIT: 定时任务并发限制
    # 建议配置范围: 15 (定时任务并发限制)
    # 调整考虑因素: 增加并发限制以提高任务执行效率；与数据库连接池大小协调，避免数据库成为瓶颈
    SCHEDULER_CONCURRENCY_LIMIT: int = 15  # 定时任务并发限制
    
    # OFFLINE_SERVER_CHECK_INTERVAL: 离线服务器检查间隔（分钟）
    # 建议配置范围: 1-10 (根据实时性要求调整)
    # 调整考虑因素: 过短会增加服务器负载和网络流量，过长可能导致状态更新不及时
    OFFLINE_SERVER_CHECK_INTERVAL: int = 2  # 离线服务器检查间隔（分钟）
    
    # OFFLINE_SERVER_WORKER_COUNT: 离线服务器检查工作者数量
    # 建议配置范围: 10-30 (根据系统资源调整)
    # 调整考虑因素: 过多会消耗系统资源，过少可能影响检查效率
    OFFLINE_SERVER_WORKER_COUNT: int = 10  # 离线服务器检查工作者数量
    
    # SERVER_ONLINE_CHECK_TIMEOUT: 服务器在线检查超时时间（秒）
    # 建议配置范围: 1-10 (根据网络环境调整)
    # 调整考虑因素: 过短可能导致检查不准确，过长会增加检查时间
    SERVER_ONLINE_CHECK_TIMEOUT: float = 3.0  # 服务器在线检查超时时间（秒）
    
    # 监控系统配置
    
    # MONITORING_ENABLED: 是否启用监控功能
    # 建议配置范围: True/False
    # 调整考虑因素: 关闭监控将失去硬件状态跟踪和告警功能，但能节省系统资源
    MONITORING_ENABLED: bool = True  # 默认启用监控
    
    # MONITORING_INTERVAL: 监控数据采集间隔（分钟）
    # 建议配置范围: 2-15 (建议在保证性能的前提下选择合适的间隔)
    # 调整考虑因素: 过短会增加服务器负载和存储压力，过长可能错过重要事件；
    # 对于大量服务器的环境，建议使用较大的间隔值
    MONITORING_INTERVAL: int = 5  # 监控数据采集间隔（分钟）
    
    # PROMETHEUS_URL: Prometheus服务地址
    # 建议配置范围: 有效的HTTP(S) URL，指向Prometheus服务
    # 调整考虑因素: 需与Docker Compose配置一致
    PROMETHEUS_URL: str = "http://prometheus:9090"
    
    # GRAFANA_URL: Grafana服务地址
    # 建议配置范围: 有效的HTTP(S) URL，指向Grafana服务
    # 调整考虑因素: 需与Docker Compose配置一致
    GRAFANA_URL: str = "http://grafana:3000"
    
    # GRAFANA_API_KEY: Grafana API密钥
    # 建议配置范围: 有效的Grafana API密钥
    # 调整考虑因素: 必须保密，泄露会导致Grafana安全风险；生产环境必须更换默认值
    GRAFANA_API_KEY: str = os.getenv("GRAFANA_API_KEY", "your-grafana-api-key-here")
    
    # REACT_APP_GRAFANA_URL: 前端访问Grafana的URL
    # 建议配置范围: 有效的HTTP(S) URL，指向Grafana服务的外部访问地址
    # 调整考虑因素: 需与Docker Compose配置一致，供前端浏览器直接访问
    REACT_APP_GRAFANA_URL: str = os.getenv("REACT_APP_GRAFANA_URL", "http://localhost:3001")
    
    # PROMETHEUS_TARGETS_PATH: Prometheus目标配置文件路径
    # 建议配置范围: 有效的文件路径，确保目录存在且有写权限
    # 调整考虑因素: 需确保目录存在且有写权限；路径需与Prometheus配置一致
    PROMETHEUS_TARGETS_PATH: str = "/etc/prometheus/targets/ipmi-targets.json"
    
    # 监控数据清理配置
    
    # MONITORING_DATA_RETENTION_DAYS: 监控数据保留天数
    # 建议配置范围: 7-365 (根据存储容量和合规要求调整)
    # 调整考虑因素: 过短可能丢失历史数据分析价值，过长会占用大量存储空间
    MONITORING_DATA_RETENTION_DAYS: int = 30  # 监控数据保留天数
    
    # MONITORING_REFRESH_INTERVAL: 监控面板刷新间隔(秒)
    # 建议配置范围: 10-60
    # 调整考虑因素: 过短会增加浏览器和服务器负载，过长可能导致数据显示滞后
    MONITORING_REFRESH_INTERVAL: int = 30  # 监控面板刷新间隔(秒)
    
    # MONITORING_DEFAULT_TIMEOUT: 监控任务默认超时时间(秒)
    # 建议配置范围: 20-60
    # 调整考虑因素: 需足够长以完成所有服务器的监控数据采集
    MONITORING_DEFAULT_TIMEOUT: int = 30  # 监控任务默认超时时间(秒)
    
    class Config:
        env_file = ".env"

settings = Settings()