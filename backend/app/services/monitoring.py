from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import time
import json
import logging

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.monitoring import MonitoringRecord
from app.models.server import Server
from app.services.ipmi import IPMIService
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class MonitoringService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ipmi_service = IPMIService()

    async def get_server_metrics(
        self, 
        server_id: int, 
        metric_type: Optional[str] = None, 
        since: Optional[datetime] = None
    ) -> List[MonitoringRecord]:
        """获取服务器监控指标"""
        try:
            # 构建查询语句
            stmt = select(MonitoringRecord).where(MonitoringRecord.server_id == server_id)
            
            if metric_type:
                stmt = stmt.where(MonitoringRecord.metric_type == metric_type)
            
            if since:
                stmt = stmt.where(MonitoringRecord.timestamp >= since)
            
            stmt = stmt.order_by(MonitoringRecord.timestamp.desc())
            
            # 执行查询
            result = await self.db.execute(stmt)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"数据库查询监控指标失败 (server_id={server_id}): {e}")
            raise ValidationError("查询监控数据失败")
        except Exception as e:
            logger.error(f"获取服务器监控指标时发生未知错误 (server_id={server_id}): {e}")
            raise ValidationError("获取监控数据失败")

    async def get_server_metrics_async(
        self, 
        server_id: int, 
        metric_type: Optional[str] = None
    ) -> List[MonitoringRecord]:
        """异步获取服务器监控指标 - 不使用时间过滤"""
        try:
            # 构建查询语句
            stmt = select(MonitoringRecord).where(MonitoringRecord.server_id == server_id)
            
            if metric_type:
                stmt = stmt.where(MonitoringRecord.metric_type == metric_type)
            
            # 注意：根据规范，不添加时间过滤条件
            stmt = stmt.order_by(MonitoringRecord.timestamp.desc())
            
            # 执行查询
            result = await self.db.execute(stmt)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"数据库查询监控指标失败 (server_id={server_id}): {e}")
            raise ValidationError("查询监控数据失败")
        except Exception as e:
            logger.error(f"获取服务器监控指标时发生未知错误 (server_id={server_id}): {e}")
            raise ValidationError("获取监控数据失败")

    async def _process_sensor_data(self, server_id: int, sensor_list: List[Dict], metric_type: str, 
                                   chinese_name: str) -> tuple[List[str], List[str], float]:
        """
        处理传感器数据的通用函数
        
        Args:
            server_id: 服务器ID
            sensor_list: 传感器数据列表
            metric_type: 指标类型 (temperature, voltage, fan_speed)
            chinese_name: 传感器类型的中文名称 (温度, 电压, 风扇)
            
        Returns:
            tuple: (收集的指标列表, 错误列表, 处理耗时)
        """
        start_time = time.time()
        collected_metrics = []
        errors = []
        
        for sensor in sensor_list:
            try:
                record = MonitoringRecord(
                    server_id=server_id,
                    metric_type=metric_type,
                    metric_name=sensor['name'],
                    value=float(sensor['value']),
                    unit=sensor['unit'],
                    status=sensor['status'],
                    raw_data=json.dumps(sensor)
                )
                self.db.add(record)
                collected_metrics.append(f"{metric_type}:{sensor['name']}")
            except Exception as e:
                error_msg = f"处理{chinese_name}传感器 {sensor.get('name', 'unknown')} 失败: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
        
        processing_time = time.time() - start_time
        logger.debug(f"[监控采集] 处理{chinese_name}传感器数据耗时: {processing_time:.3f}秒")
        
        return collected_metrics, errors, processing_time

    async def collect_server_metrics(self, server_id: int) -> Dict[str, Any]:
        """采集服务器指标数据并删除旧数据"""
        start_time = time.time()
        logger.debug(f"[监控采集] 开始采集服务器 {server_id} 的监控指标")
        
        # 获取服务器信息
        server_info_start = time.time()
        # 使用异步查询方式
        stmt = select(Server).where(Server.id == server_id)
        result = await self.db.execute(stmt)
        server = result.scalar_one_or_none()
        server_info_time = time.time() - server_info_start
        logger.debug(f"[监控采集] 获取服务器信息耗时: {server_info_time:.3f}秒")
        
        if not server:
            raise ValidationError("服务器不存在")
        
        try:
            # 步骤 1: 先删除此服务器的所有旧数据
            cleanup_start = time.time()
            try:
                stmt = delete(MonitoringRecord).where(MonitoringRecord.server_id == server_id)
                result = await self.db.execute(stmt)
                deleted_count = result.rowcount
                logger.info(f"成功删除服务器 {server_id} 的 {deleted_count} 条旧监控数据")
            except Exception as e:
                await self.db.rollback()
                logger.error(f"删除旧监控数据失败 (server_id={server_id}): {e}")
                return {
                    "status": "error",
                    "message": "删除旧监控数据失败",
                    "timestamp": datetime.now().isoformat()
                }
            cleanup_time = time.time() - cleanup_start
            logger.debug(f"[监控采集] 删除旧数据耗时: {cleanup_time:.3f}秒")

            # 步骤 2: 获取并处理新的传感器数据
            sensor_start = time.time()
            logger.debug(f"[监控采集] 开始获取服务器 {server_id} 的传感器数据")
            sensor_data = await self.ipmi_service.get_sensor_data(
                ip=server.ipmi_ip,
                username=server.ipmi_username,
                password=server.ipmi_password,
                port=server.ipmi_port
            )
            sensor_time = time.time() - sensor_start
            logger.debug(f"[监控采集] 获取传感器数据耗时: {sensor_time:.3f}秒")
            
            # 记录传感器数据统计信息
            temp_count = len(sensor_data.get('temperature', []))
            voltage_count = len(sensor_data.get('voltage', []))
            fan_count = len(sensor_data.get('fan_speed', []))
            logger.debug(f"[监控采集] 传感器数据统计 - 温度: {temp_count}, 电压: {voltage_count}, 风扇: {fan_count}")
            
            collected_metrics = []
            errors = []
            
            # 处理温度传感器
            temp_metrics, temp_errors, temp_time = await self._process_sensor_data(
                server_id, sensor_data.get('temperature', []), 'temperature', '温度'
            )
            collected_metrics.extend(temp_metrics)
            errors.extend(temp_errors)
            
            # 处理电压传感器
            voltage_metrics, voltage_errors, voltage_time = await self._process_sensor_data(
                server_id, sensor_data.get('voltage', []), 'voltage', '电压'
            )
            collected_metrics.extend(voltage_metrics)
            errors.extend(voltage_errors)
            
            # 处理风扇转速传感器
            fan_metrics, fan_errors, fan_time = await self._process_sensor_data(
                server_id, sensor_data.get('fan_speed', []), 'fan_speed', '风扇'
            )
            collected_metrics.extend(fan_metrics)
            errors.extend(fan_errors)
            
            logger.info(f"[监控采集] 处理完成，共收集 {len(collected_metrics)} 个指标")
            
            # 步骤 3: 提交新数据到数据库
            commit_start = time.time()
            try:
                # 提交在步骤2中暂存到会话中的新数据
                await self.db.commit()
                logger.info(f"成功保存服务器 {server_id} 的 {len(collected_metrics)} 条新监控记录到数据库")
                
                # 添加验证步骤：查询刚保存的数据
                stmt = select(MonitoringRecord).where(MonitoringRecord.server_id == server_id)
                result = await self.db.execute(stmt)
                saved_records = result.scalars().all()
                logger.debug(f"验证步骤：服务器 {server_id} 数据库中现有记录数: {len(saved_records)}")
            except SQLAlchemyError as e:
                await self.db.rollback()
                logger.error(f"保存新监控数据到数据库失败 (server_id={server_id}): {e}")
                return {
                    "status": "error",
                    "message": "保存新监控数据到数据库失败",
                    "timestamp": datetime.now().isoformat()
                }
            commit_time = time.time() - commit_start
            logger.debug(f"[监控采集] 数据库提交耗时: {commit_time:.3f}秒")
            
            total_time = time.time() - start_time
            logger.debug(f"[监控采集] 服务器 {server_id} 监控指标采集总耗时: {total_time:.3f}秒")
            
            result = {
                "status": "success",
                "collected_metrics": collected_metrics,
                "timestamp": datetime.now().isoformat(),
                "execution_time": {
                    "total": round(total_time, 3),
                    "server_info": round(server_info_time, 3),
                    "sensor_data": round(sensor_time, 3),
                    "temperature_processing": round(temp_time, 3),
                    "voltage_processing": round(voltage_time, 3),
                    "fan_processing": round(fan_time, 3),
                    "cleanup": round(cleanup_time, 3),
                    "database_commit": round(commit_time, 3)
                }
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
                await self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"回滚数据库事务失败: {rollback_error}")
            
            total_time = time.time() - start_time
            logger.error(f"[监控采集] 采集服务器 {server_id} 指标失败，总耗时: {total_time:.3f}秒, 错误: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat(),
                "execution_time": {
                    "total": round(total_time, 3)
                }
            }