from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError

from app.models.monitoring import MonitoringRecord
from app.models.server import Server
from app.services.ipmi import IPMIService
from app.core.exceptions import ValidationError
import json
import logging

logger = logging.getLogger(__name__)

class MonitoringService:
    def __init__(self, db: Session):
        self.db = db
        self.ipmi_service = IPMIService()

    def get_server_metrics(
        self, 
        server_id: int, 
        metric_type: Optional[str] = None, 
        since: Optional[datetime] = None
    ) -> List[MonitoringRecord]:
        """获取服务器监控指标"""
        try:
            query = self.db.query(MonitoringRecord).filter(MonitoringRecord.server_id == server_id)
            
            if metric_type:
                query = query.filter(MonitoringRecord.metric_type == metric_type)
            
            if since:
                query = query.filter(MonitoringRecord.timestamp >= since)
            
            return query.order_by(MonitoringRecord.timestamp.desc()).all()
            
        except SQLAlchemyError as e:
            logger.error(f"数据库查询监控指标失败 (server_id={server_id}): {e}")
            raise ValidationError("查询监控数据失败")
        except Exception as e:
            logger.error(f"获取服务器监控指标时发生未知错误 (server_id={server_id}): {e}")
            raise ValidationError("获取监控数据失败")

    async def collect_server_metrics(self, server_id: int) -> Dict[str, Any]:
        """采集服务器指标数据"""
        # 获取服务器信息
        server = self.db.query(Server).filter(Server.id == server_id).first()
        if not server:
            raise ValidationError("服务器不存在")
        
        try:
            # 获取传感器数据
            sensor_data = await self.ipmi_service.get_sensor_data(
                ip=server.ipmi_ip,
                username=server.ipmi_username,
                password=server.ipmi_password,
                port=server.ipmi_port
            )
            
            collected_metrics = []
            errors = []
            
            # 处理温度传感器
            for temp_sensor in sensor_data.get('temperature', []):
                try:
                    record = MonitoringRecord(
                        server_id=server_id,
                        metric_type='temperature',
                        metric_name=temp_sensor['name'],
                        value=float(temp_sensor['value']),
                        unit=temp_sensor['unit'],
                        status=temp_sensor['status'],
                        raw_data=json.dumps(temp_sensor)
                    )
                    self.db.add(record)
                    collected_metrics.append(f"temperature:{temp_sensor['name']}")
                except Exception as e:
                    error_msg = f"处理温度传感器 {temp_sensor.get('name', 'unknown')} 失败: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            
            # 处理电压传感器
            for voltage_sensor in sensor_data.get('voltage', []):
                try:
                    record = MonitoringRecord(
                        server_id=server_id,
                        metric_type='voltage',
                        metric_name=voltage_sensor['name'],
                        value=float(voltage_sensor['value']),
                        unit=voltage_sensor['unit'],
                        status=voltage_sensor['status'],
                        raw_data=json.dumps(voltage_sensor)
                    )
                    self.db.add(record)
                    collected_metrics.append(f"voltage:{voltage_sensor['name']}")
                except Exception as e:
                    error_msg = f"处理电压传感器 {voltage_sensor.get('name', 'unknown')} 失败: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            
            # 处理风扇转速传感器
            for fan_sensor in sensor_data.get('fan_speed', []):
                try:
                    record = MonitoringRecord(
                        server_id=server_id,
                        metric_type='fan_speed',
                        metric_name=fan_sensor['name'],
                        value=float(fan_sensor['value']),
                        unit=fan_sensor['unit'],
                        status=fan_sensor['status'],
                        raw_data=json.dumps(fan_sensor)
                    )
                    self.db.add(record)
                    collected_metrics.append(f"fan_speed:{fan_sensor['name']}")
                except Exception as e:
                    error_msg = f"处理风扇传感器 {fan_sensor.get('name', 'unknown')} 失败: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            
            # 提交数据库事务
            try:
                self.db.commit()
                logger.info(f"成功保存服务器 {server_id} 的 {len(collected_metrics)} 条监控记录到数据库")
            except SQLAlchemyError as e:
                self.db.rollback()
                logger.error(f"保存监控数据到数据库失败 (server_id={server_id}): {e}")
                return {
                    "status": "error",
                    "message": "保存监控数据到数据库失败",
                    "timestamp": datetime.now().isoformat()
                }
            
            result = {
                "status": "success",
                "collected_metrics": collected_metrics,
                "timestamp": datetime.now().isoformat()
            }
            
            # 如果有错误，但有成功采集的数据，则标记为部分成功
            if errors and collected_metrics:
                result["status"] = "partial_success"
                result["errors"] = errors
                logger.warning(f"服务器 {server_id} 指标采集部分成功，错误: {errors}")
            elif errors:
                result["status"] = "error"
                result["errors"] = errors
            
            return result
            
        except Exception as e:
            # 回滚数据库事务
            try:
                self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"回滚数据库事务失败: {rollback_error}")
            
            logger.error(f"采集服务器 {server_id} 指标失败: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def cleanup_old_metrics(self, days: int = 30) -> int:
        """清理旧的监控数据"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        deleted_count = self.db.query(MonitoringRecord).filter(
            MonitoringRecord.timestamp < cutoff_date
        ).delete()
        
        self.db.commit()
        return deleted_count