import os
import shutil
import logging
from datetime import datetime
from typing import List
from pathlib import Path
import aiofiles
import sqlite3

from app.core.config import settings

logger = logging.getLogger(__name__)

class BackupService:
    def __init__(self):
        # 确保备份目录存在
        self.backup_dir = Path("./backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        
    def create_backup(self) -> str:
        """创建数据库备份"""
        logger.debug("开始创建数据库备份")
        try:
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # 使用SQLite在线备份机制确保数据一致性
            self._sqlite_online_backup(backup_path)
            
            logger.info(f"数据库备份创建成功: {backup_path}")
            return backup_filename
        except Exception as e:
            logger.error(f"创建数据库备份失败: {e}")
            raise
            
    def _sqlite_online_backup(self, backup_path: Path):
        """使用SQLite在线备份机制创建一致的备份"""
        logger.debug("使用SQLite在线备份机制创建数据库备份")
        try:
            # 连接到源数据库
            source_conn = sqlite3.connect(self.db_path)
            
            # 连接到目标备份数据库
            backup_conn = sqlite3.connect(str(backup_path))
            
            # 执行在线备份
            source_conn.backup(backup_conn)
            
            # 关闭连接
            source_conn.close()
            backup_conn.close()
            
            logger.info("SQLite在线备份完成")
        except Exception as e:
            logger.error(f"SQLite在线备份失败: {e}")
            raise
            
    def list_backups(self) -> List[dict]:
        """列出所有备份文件"""
        logger.debug("开始列出备份文件")
        backups = []
        try:
            for file_path in self.backup_dir.glob("*.db"):
                if file_path.is_file():
                    stat = file_path.stat()
                    backups.append({
                        "filename": file_path.name,
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime),
                        "file_path": str(file_path)
                    })
            
            # 按创建时间排序
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            logger.info(f"成功列出 {len(backups)} 个备份文件")
            return backups
        except Exception as e:
            logger.error(f"列出备份文件失败: {e}")
            raise
            
    def delete_backup(self, filename: str) -> bool:
        """删除备份文件"""
        logger.debug(f"开始删除备份文件: {filename}")
        try:
            backup_path = self.backup_dir / filename
            if backup_path.exists() and backup_path.is_file():
                backup_path.unlink()
                logger.info(f"备份文件删除成功: {filename}")
                return True
            else:
                logger.warning(f"备份文件不存在: {filename}")
                return False
        except Exception as e:
            logger.error(f"删除备份文件失败: {e}")
            raise
            
    def restore_backup(self, filename: str) -> bool:
        """恢复数据库备份"""
        logger.debug(f"开始恢复数据库备份: {filename}")
        try:
            backup_path = self.backup_dir / filename
            if not backup_path.exists() or not backup_path.is_file():
                logger.error(f"备份文件不存在: {filename}")
                raise FileNotFoundError(f"备份文件不存在: {filename}")
            
            # 使用SQLite在线恢复机制确保数据一致性
            self._sqlite_online_restore(backup_path)
            
            logger.info(f"数据库备份恢复成功: {filename}")
            return True
        except Exception as e:
            logger.error(f"恢复数据库备份失败: {e}")
            raise
            
    def _sqlite_online_restore(self, backup_path: Path):
        """使用SQLite在线恢复机制恢复备份"""
        logger.debug("使用SQLite在线恢复机制恢复数据库备份")
        try:
            # 连接到备份数据库
            backup_conn = sqlite3.connect(str(backup_path))
            
            # 连接到目标数据库
            target_conn = sqlite3.connect(self.db_path)
            
            # 执行在线恢复
            backup_conn.backup(target_conn)
            
            # 关闭连接
            backup_conn.close()
            target_conn.close()
            
            logger.info("SQLite在线恢复完成")
        except Exception as e:
            logger.error(f"SQLite在线恢复失败: {e}")
            raise
            
    def verify_backup(self, filename: str) -> dict:
        """验证备份文件完整性"""
        logger.debug(f"开始验证备份文件完整性: {filename}")
        try:
            backup_path = self.backup_dir / filename
            if not backup_path.exists() or not backup_path.is_file():
                logger.error(f"备份文件不存在: {filename}")
                return {
                    "filename": filename,
                    "is_valid": False,
                    "message": "备份文件不存在"
                }
            
            # 尝试连接数据库文件验证完整性
            try:
                conn = sqlite3.connect(backup_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check;")
                result = cursor.fetchone()
                conn.close()
                
                is_valid = result[0] == "ok"
                message = "备份文件完整" if is_valid else "备份文件损坏"
                
                logger.info(f"备份文件验证完成: {filename}, 结果: {message}")
                return {
                    "filename": filename,
                    "is_valid": is_valid,
                    "message": message
                }
            except sqlite3.DatabaseError as e:
                logger.error(f"备份文件验证失败: {e}")
                return {
                    "filename": filename,
                    "is_valid": False,
                    "message": f"备份文件损坏: {str(e)}"
                }
        except Exception as e:
            logger.error(f"验证备份文件失败: {e}")
            return {
                "filename": filename,
                "is_valid": False,
                "message": f"验证过程出错: {str(e)}"
            }