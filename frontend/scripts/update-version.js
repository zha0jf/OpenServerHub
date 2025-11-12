/**
 * 版本信息更新脚本
 * 在构建时自动从 Git 获取版本信息
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const versionFilePath = path.join(__dirname, '../src/config/version.ts');

try {
  // 获取 Git 信息：使用 git describe 获取 tag-commit 格式
  let versionString = 'unknown';

  try {
    // 使用 git describe 获取描述性版本字符串
    // 如果在 tag 后有 commit，格式为 "tag-number-ghash"
    // 如果恰好在 tag 上，格式为 "tag"
    versionString = execSync('git describe --tags --always', { encoding: 'utf-8' }).trim();
  } catch (e) {
    console.warn('Warning: Could not get git information');
    versionString = 'unknown';
  }

  // 获取 CST 时区的时间
  const now = new Date();
  const cstTime = now.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });

  const content = `/**
 * 版本信息配置
 * 此文件在构建时会被自动更新
 */

export const VERSION_INFO = {
  // 版本字符串，格式: tag-commits-ghash 或 tag 或 commit
  version: '${versionString}',
  // 构建时间（CST 时区）
  buildTime: '${cstTime}',
};
`;

  fs.writeFileSync(versionFilePath, content, 'utf-8');
  console.log(`✓ Updated version info: ${versionString} (${cstTime})`);
} catch (error) {
  console.error('Error updating version:', error.message);
  process.exit(1);
}
