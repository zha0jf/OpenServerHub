import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Space,
  Table,
  Typography,
  message,
  Modal,
  Select,
  Row,
  Col,
  Divider,
  Upload,
  Progress,
  Tag,
  Tooltip,
  Alert,
  Checkbox,
  InputNumber,
} from 'antd';
import {
  SearchOutlined,
  ImportOutlined,
  DownloadOutlined,
  UploadOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { ColumnsType } from 'antd/es/table';
import { discoveryService, DiscoveredDevice, NetworkScanResponse, NetworkExamples } from '../../services/discovery';
import { serverService, ServerGroup } from '../../services/server';
import type { UploadProps } from 'antd';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { Dragger } = Upload;

interface ScanProgress {
  isScanning: boolean;
  progress: number;
  status: string;
}

const DeviceDiscovery: React.FC = () => {
  const [form] = Form.useForm();
  const [csvForm] = Form.useForm();
  const [scanResults, setScanResults] = useState<DiscoveredDevice[]>([]);
  const [scanProgress, setScanProgress] = useState<ScanProgress>({
    isScanning: false,
    progress: 0,
    status: '',
  });
  const [selectedDevices, setSelectedDevices] = useState<React.Key[]>([]);
  const [groups, setGroups] = useState<ServerGroup[]>([]);
  const [networkExamples, setNetworkExamples] = useState<NetworkExamples | null>(null);
  const [csvModalVisible, setCSVModalVisible] = useState(false);
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [examplesModalVisible, setExamplesModalVisible] = useState(false);
  const [lastScanInfo, setLastScanInfo] = useState<{
    total: number;
    found: number;
    duration: number;
  } | null>(null);

  useEffect(() => {
    loadGroups();
    loadNetworkExamples();
  }, []);

  const loadGroups = async () => {
    try {
      const data = await serverService.getServerGroups();
      setGroups(data);
    } catch (error) {
      console.error('加载分组列表失败:', error);
    }
  };

  const loadNetworkExamples = async () => {
    try {
      const examples = await discoveryService.getNetworkExamples();
      setNetworkExamples(examples);
    } catch (error) {
      console.error('加载网络示例失败:', error);
    }
  };

  const handleNetworkScan = async (values: any) => {
    let progressInterval: NodeJS.Timeout | null = null;
    
    try {
      setScanProgress({
        isScanning: true,
        progress: 0,
        status: '开始扫描网络...',
      });
      setScanResults([]);
      setLastScanInfo(null);

      // 根据公式计算实际超时时间：超时时间=（待扫描IP数/并发数）*（超时时间+1）+50s
      // 计算待扫描IP数
       let ipCount = 0;
       if (values.network.includes('/')) {
         // CIDR格式
         try {
           const [ip, prefix] = values.network.split('/');
           const subnet = Math.pow(2, 32 - parseInt(prefix));
           ipCount = subnet - 2; // 排除网络地址和广播地址
         } catch (e) {
           ipCount = 254; // 默认C类网络
         }
       } else if (values.network.includes('-')) {
         // IP范围格式
         const ips = values.network.split('-');
         if (ips.length === 2) {
           // 简化计算，实际应该计算IP范围
           ipCount = 100; // 默认值
         } else {
           ipCount = 1;
         }
       } else if (values.network.includes(',')) {
         // 逗号分隔格式
         ipCount = values.network.split(',').length;
       } else {
         // 单个IP
         ipCount = 1;
       }
      const calculatedTimeout = Math.ceil((ipCount / (values.max_workers || 5)) * ((values.timeout || 3) + 2)) + 50;
      
      // 动态调整进度条更新逻辑
      let currentProgress = 0;
      const progressIncrement = 100 / (calculatedTimeout * 2); // 每500ms更新一次进度
      progressInterval = setInterval(() => {
        currentProgress = Math.min(currentProgress + progressIncrement, 95); // 最大到95%
        setScanProgress(prev => ({
          ...prev,
          progress: currentProgress,
          status: `扫描中... ${Math.floor(currentProgress)}%`,
        }));
      }, 500);

      const result: NetworkScanResponse = await discoveryService.scanNetwork({
        network: values.network,
        port: values.port || 623,
        timeout: values.timeout || 3,
        max_workers: values.max_workers || 10,
        calculated_timeout: calculatedTimeout, // 传递计算后的超时时间
      });

      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      
      // 确保进度显示100%
      setScanProgress({
        isScanning: false,
        progress: 100,
        status: `扫描完成！发现 ${result.devices_found} 个设备`,
      });
      
      setScanResults(result.devices);
      setLastScanInfo({
        total: result.total_scanned,
        found: result.devices_found,
        duration: result.scan_duration,
      });
      
      if (result.devices_found > 0) {
        message.success(`网络扫描完成！扫描了 ${result.total_scanned} 个IP，发现 ${result.devices_found} 个BMC设备，请查看下方设备列表`);
      } else {
        message.info(`网络扫描完成！扫描了 ${result.total_scanned} 个IP，未发现BMC设备。请检查网络配置或尝试其他网络范围。`);
      }
    } catch (error: any) {
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      
      setScanProgress({
        isScanning: false,
        progress: 0,
        status: '扫描失败',
      });
      
      // 清空结果和统计信息
      setScanResults([]);
      setLastScanInfo(null);
      
      console.error('网络扫描失败:', error);
      
      // 根据错误类型显示不同的错误信息
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        message.error('网络扫描超时，请检查网络连接或减少扫描范围');
      } else if (error.response?.status === 400) {
        // 400错误已由全局拦截器处理，这里不重复显示
      } else {
        message.error('网络扫描失败，请检查网络配置或稍后重试');
      }
    }
  };

  const handleBatchImport = async () => {
    // 只允许对未添加的设备进行批量导入
    const selectedNewDevices = scanResults.filter(device => 
      selectedDevices.includes(device.ip) && !device.already_exists
    );
    
    if (selectedNewDevices.length === 0) {
      message.warning('请选择未添加的设备进行导入');
      return;
    }

    setImportModalVisible(true);
  };

  const handleImportSubmit = async (values: any) => {
    try {
      // 过滤出选中的未添加设备
      const selectedDeviceData = scanResults.filter(device => 
        selectedDevices.includes(device.ip) && !device.already_exists
      );

      const result = await discoveryService.batchImportDevices({
        devices: selectedDeviceData,
        default_username: values.default_username || '',
        default_password: values.default_password || '',
        group_id: values.group_id,
      });

      message.success(`批量导入完成！成功导入 ${result.success_count} 台设备`);
      
      if (result.failed_count > 0) {
        Modal.warning({
          title: '部分设备导入失败',
          content: (
            <div>
              <p>以下设备导入失败：</p>
              <ul>
                {result.failed_details.map((detail, index) => (
                  <li key={index}>
                    {detail.ip}: {detail.error}
                  </li>
                ))}
              </ul>
            </div>
          ),
          width: 600,
        });
      }

      setImportModalVisible(false);
      setSelectedDevices([]);
      
      // 刷新扫描结果，重新扫描以更新设备状态
      if (result.success_count > 0) {
        message.info('正在刷新设备列表...');
        // 可以选择重新扫描或直接更新状态
      }
    } catch (error) {
      console.error('批量导入失败:', error);
    }
  };

  const handleCSVImport = async (values: any) => {
    try {
      const result = await discoveryService.importFromCSVText({
        csv_content: values.csv_content,
        group_id: values.group_id,
      });

      message.success(`CSV导入完成！成功导入 ${result.success_count} 台服务器`);
      
      if (result.failed_count > 0) {
        Modal.warning({
          title: '部分数据导入失败',
          content: (
            <div>
              <p>以下行导入失败：</p>
              <ul>
                {result.failed_details.map((detail, index) => (
                  <li key={index}>
                    第{detail.row}行 ({detail.name} - {detail.ipmi_ip}): {detail.error}
                  </li>
                ))}
              </ul>
            </div>
          ),
          width: 700,
        });
      }

      setCSVModalVisible(false);
      csvForm.resetFields();
    } catch (error) {
      console.error('CSV导入失败:', error);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const template = await discoveryService.downloadCSVTemplate();
      const blob = new Blob([template], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', 'server_import_template.csv');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      message.success('CSV模板下载成功');
    } catch (error) {
      console.error('下载模板失败:', error);
    }
  };

  const uploadProps: UploadProps = {
    name: 'csv_file',
    accept: '.csv',
    beforeUpload: (file) => {
      if (!file.name.endsWith('.csv')) {
        message.error('请上传CSV格式的文件');
        return false;
      }
      return false; // 阻止自动上传
    },
    customRequest: async ({ file, onSuccess, onError }) => {
      try {
        const result = await discoveryService.importFromCSVFile(file as File);
        message.success(`CSV文件导入完成！成功导入 ${result.success_count} 台服务器`);
        onSuccess?.(result);
      } catch (error) {
        console.error('CSV文件导入失败:', error);
        onError?.(error as Error);
      }
    },
  };

  const getAccessibilityTag = (device: DiscoveredDevice) => {
    if (device.accessible) {
      return <Tag color="green" icon={<CheckCircleOutlined />}>可访问</Tag>;
    } else {
      return <Tag color="orange" icon={<ExclamationCircleOutlined />}>需要认证</Tag>;
    }
  };

  const getDeviceStatusTag = (device: DiscoveredDevice) => {
    if (device.already_exists) {
      return (
        <Tooltip title={`已添加为: ${device.existing_server_name}`}>
          <Tag color="blue" icon={<CheckCircleOutlined />}>已添加</Tag>
        </Tooltip>
      );
    } else {
      return <Tag color="green">未添加</Tag>;
    }
  };

  const columns: ColumnsType<DiscoveredDevice> = [
    {
      title: 'IP地址',
      dataIndex: 'ip',
      key: 'ip',
      fixed: 'left',
      width: 140,
    },
    {
      title: '端口',
      dataIndex: 'port',
      key: 'port',
      width: 80,
    },
    {
      title: '访问状态',
      key: 'accessibility',
      width: 100,
      render: (_, device) => getAccessibilityTag(device),
    },
    {
      title: '设备状态',
      key: 'device_status',
      width: 100,
      render: (_, device) => getDeviceStatusTag(device),
    },
    {
      title: '制造商',
      dataIndex: 'manufacturer',
      key: 'manufacturer',
      width: 120,
      render: (text) => text || '-',
    },
    {
      title: '型号',
      dataIndex: 'model',
      key: 'model',
      width: 150,
      render: (text) => text || '-',
    },
    {
      title: '序列号',
      dataIndex: 'serial_number',
      key: 'serial_number',
      width: 120,
      render: (text) => text || '-',
    },
    {
      title: 'BMC版本',
      dataIndex: 'bmc_version',
      key: 'bmc_version',
      width: 120,
      render: (text) => text || '-',
    },
    {
      title: '凭据',
      key: 'credentials',
      width: 120,
      render: (_, device) => {
        if (device.username || device.password) {
          return (
            <Tooltip title={`用户名: ${device.username}, 密码: ${'*'.repeat(device.password.length)}`}>
              <Tag color="blue">已发现</Tag>
            </Tooltip>
          );
        }
        return <Tag color="default">需配置</Tag>;
      },
    },
  ];

  const rowSelection = {
    selectedRowKeys: selectedDevices,
    onChange: (selectedRowKeys: React.Key[]) => {
      setSelectedDevices(selectedRowKeys);
    },
    getCheckboxProps: (record: DiscoveredDevice) => ({
      disabled: false,
    }),
  };

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <Title level={2}>设备发现</Title>
            <Paragraph>
              通过网络扫描自动发现BMC设备，支持批量导入和CSV文件导入。
            </Paragraph>
          </Card>
        </Col>

        {/* 网络扫描配置 */}
        <Col span={24}>
          <Card title="网络扫描配置" extra={
            <Button 
              icon={<InfoCircleOutlined />} 
              type="link" 
              onClick={() => setExamplesModalVisible(true)}
            >
              查看格式示例
            </Button>
          }>
            <Form
              form={form}
              layout="vertical"
              onFinish={handleNetworkScan}
              initialValues={{
                port: 623,
                timeout: 3,
                max_workers: 5,
              }}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="network"
                    label="网络范围"
                    rules={[{ required: true, message: '请输入网络范围' }]}
                    extra="支持CIDR格式 (192.168.1.0/24)、IP范围 (192.168.1.1-192.168.1.100) 或逗号分隔的IP列表 (192.168.1.1,192.168.1.2)"
                  >
                    <Input placeholder="例如: 192.168.1.0/24 或 192.168.1.1-192.168.1.100 或 192.168.1.1,192.168.1.2" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item name="port" label="IPMI端口">
                    <InputNumber min={1} max={65535} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={3}>
                  <Form.Item name="timeout" label="超时时间(秒)">
                    <InputNumber min={1} max={30} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={3}>
                  <Form.Item name="max_workers" label="并发数">
                    <Select style={{ width: '100%' }}>
                      <Select.Option value={1}>1</Select.Option>
                      <Select.Option value={3}>3</Select.Option>
                      <Select.Option value={5}>5</Select.Option>
                      <Select.Option value={10}>10</Select.Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
              <Form.Item>
                <Space>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    icon={<SearchOutlined />}
                    loading={scanProgress.isScanning}
                  >
                    {scanProgress.isScanning ? '扫描中...' : '开始扫描'}
                  </Button>
                  <Button icon={<UploadOutlined />} onClick={() => setCSVModalVisible(true)}>
                    CSV导入
                  </Button>
                  <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>
                    下载模板
                  </Button>
                </Space>
              </Form.Item>
            </Form>

            {/* 扫描进度 */}
            {(scanProgress.isScanning || scanProgress.progress > 0) && (
              <div style={{ marginTop: 16 }}>
                <Text>{scanProgress.status}</Text>
                <Progress 
                  percent={Math.round(scanProgress.progress)} 
                  status={scanProgress.isScanning ? 'active' : (scanProgress.progress === 100 ? 'success' : 'normal')}
                  style={{ marginTop: 8 }}
                  showInfo={true}
                  format={(percent) => `${percent}%`}
                />
                {scanProgress.progress === 100 && !scanProgress.isScanning && (
                  <div style={{ marginTop: 8, color: '#52c41a' }}>
                    ✓ 扫描任务已完成
                  </div>
                )}
              </div>
            )}

            {/* 扫描结果摘要 */}
            {lastScanInfo && (
              <Alert
                message={`扫描完成 - 发现 ${lastScanInfo.found} 个设备`}
                description={
                  <div>
                    <Text>扫描了 <strong>{lastScanInfo.total}</strong> 个IP地址，</Text>
                    <Text>发现 <strong>{lastScanInfo.found}</strong> 个BMC设备，</Text>
                    <Text>耗时 <strong>{lastScanInfo.duration}</strong> 秒</Text>
                    {lastScanInfo.found > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <Text type="success">
                          ✓ 请查看下方设备列表，选择需要导入的设备
                        </Text>
                      </div>
                    )}
                    {lastScanInfo.found === 0 && (
                      <div style={{ marginTop: 8 }}>
                        <Text type="warning">
                          ⚠ 未发现设备，请检查网络配置或尝试其他网络范围
                        </Text>
                      </div>
                    )}
                  </div>
                }
                type={lastScanInfo.found > 0 ? "success" : "info"}
                showIcon
                style={{ marginTop: 16 }}
              />
            )}
          </Card>
        </Col>

        {/* 发现的设备列表 */}
        {scanResults.length > 0 && (
          <Col span={24}>
            <Card 
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  <span>发现的BMC设备 ({scanResults.length})</span>
                  <Tag color="green">{scanResults.filter(d => !d.already_exists).length} 未添加</Tag>
                  <Tag color="blue">{scanResults.filter(d => d.already_exists).length} 已添加</Tag>
                </div>
              }
              extra={
                <Space>
                  <Button 
                    type="primary" 
                    icon={<ImportOutlined />}
                    onClick={handleBatchImport}
                    disabled={selectedDevices.length === 0}
                    size="small"
                  >
                    批量导入 ({selectedDevices.length})
                  </Button>
                  <Button 
                    size="small"
                    onClick={() => {
                      // 只选择未添加的设备
                      const newDeviceIps = scanResults
                        .filter(device => !device.already_exists)
                        .map(device => device.ip);
                      setSelectedDevices(newDeviceIps);
                    }}
                  >
                    全选未添加
                  </Button>
                  <Button 
                    size="small"
                    onClick={() => setSelectedDevices([])}
                  >
                    清空
                  </Button>
                </Space>
              }
              style={{
                border: '2px solid #52c41a',
                borderRadius: '8px'
              }}
            >
              <div style={{ marginBottom: 16 }}>
                <Alert
                  message="发现设备成功"
                  description={
                    <div>
                      <Text>以下是扫描发现的BMC设备，已按状态分组显示：</Text>
                      <br />
                      <Text type="success">
                        • <Tag color="green">未添加</Tag>：可导入到系统中的新设备
                      </Text>
                      <br />
                      <Text type="secondary">
                        • <Tag color="blue">已添加</Tag>：已在系统中的设备，仅用于查看
                      </Text>
                      <br />
                      <Text type="secondary">
                        • <Tag color="green" icon={<CheckCircleOutlined />}>可访问</Tag>：表示设备可直接访问，已发现默认凭据
                      </Text>
                      <br />
                      <Text type="secondary">
                        • <Tag color="orange" icon={<ExclamationCircleOutlined />}>需要认证</Tag>：表示设备需要配置凭据
                      </Text>
                    </div>
                  }
                  type="info"
                  showIcon
                />
              </div>
              
              {/* 未添加的设备列表 */}
              {scanResults.filter(d => !d.already_exists).length > 0 && (
                <div style={{ marginBottom: 24 }}>
                  <Title level={5} style={{ color: '#52c41a' }}>
                    未添加设备 ({scanResults.filter(d => !d.already_exists).length})
                  </Title>
                  <Table
                columns={columns}
                dataSource={scanResults.filter(d => !d.already_exists)}
                rowKey="ip"
                rowSelection={{
                  selectedRowKeys: selectedDevices,
                  onChange: (selectedRowKeys: React.Key[]) => {
                    setSelectedDevices(selectedRowKeys);
                  },
                  getCheckboxProps: (record: DiscoveredDevice) => ({
                    disabled: record.already_exists,
                  }),
                }}
                    scroll={{ x: 1000 }}
                    size="small"
                    pagination={{
                      showSizeChanger: true,
                      showQuickJumper: true,
                      showTotal: (total, range) => `第 ${range?.[0]}-${range?.[1]} 条，共 ${total} 条记录`,
                      pageSize: 10,
                    }}
                    style={{
                      marginTop: 8
                    }}
                  />
                </div>
              )}
              
              {/* 已添加的设备列表 */}
              {scanResults.filter(d => d.already_exists).length > 0 && (
                <div>
                  <Title level={5} style={{ color: '#1890ff' }}>
                    已添加设备 ({scanResults.filter(d => d.already_exists).length})
                  </Title>
                  <Table
                columns={columns}
                dataSource={scanResults.filter(d => d.already_exists)}
                rowKey="ip"
                rowSelection={{
                  selectedRowKeys: selectedDevices,
                  onChange: (selectedRowKeys: React.Key[]) => {
                    setSelectedDevices(selectedRowKeys);
                  },
                  getCheckboxProps: (record: DiscoveredDevice) => ({
                    disabled: record.already_exists,
                  }),
                }}
                scroll={{ x: 1000 }}
                size="small"
                    pagination={{
                      showSizeChanger: true,
                      showQuickJumper: true,
                      showTotal: (total, range) => `第 ${range?.[0]}-${range?.[1]} 条，共 ${total} 条记录`,
                      pageSize: 10,
                    }}
                    style={{
                      marginTop: 8
                    }}
                  />
                </div>
              )}
            </Card>
          </Col>
        )}
      </Row>

      {/* 批量导入模态框 */}
      <Modal
        title={`批量导入设备 - 已选择 ${selectedDevices.length} 台设备`}
        open={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          layout="vertical"
          onFinish={handleImportSubmit}
        >
          <Form.Item 
            name="default_username" 
            label="默认IPMI用户名"
            extra="为未发现凭据的设备设置默认用户名"
          >
            <Input placeholder="默认IPMI用户名" />
          </Form.Item>
          
          <Form.Item 
            name="default_password" 
            label="默认IPMI密码"
            extra="为未发现凭据的设备设置默认密码"
          >
            <Input.Password placeholder="默认IPMI密码" />
          </Form.Item>
          
          <Form.Item name="group_id" label="目标分组">
            <Select placeholder="选择分组（可选）" allowClear>
              {groups.map(group => (
                <Option key={group.id} value={group.id}>{group.name}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                确认导入
              </Button>
              <Button onClick={() => setImportModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* CSV导入模态框 */}
      <Modal
        title="CSV导入服务器"
        open={csvModalVisible}
        onCancel={() => setCSVModalVisible(false)}
        footer={null}
        width={800}
      >
        <Form
          form={csvForm}
          layout="vertical"
          onFinish={handleCSVImport}
        >
          <Form.Item>
            <Alert
              message="CSV格式要求"
              description="CSV文件必须包含以下列：name, ipmi_ip, ipmi_username, ipmi_password, ipmi_port, manufacturer, model, serial_number, description"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          </Form.Item>
          
          <Form.Item
            name="csv_content"
            label="CSV内容"
            rules={[{ required: true, message: '请输入CSV内容' }]}
          >
            <TextArea 
              rows={8} 
              placeholder="粘贴CSV内容，或使用下方文件上传功能"
            />
          </Form.Item>
          
          <Form.Item label="或上传CSV文件">
            <Dragger {...uploadProps}>
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽CSV文件到此区域上传</p>
              <p className="ant-upload-hint">仅支持.csv格式文件</p>
            </Dragger>
          </Form.Item>
          
          <Form.Item name="group_id" label="目标分组">
            <Select placeholder="选择分组（可选）" allowClear>
              {groups.map(group => (
                <Option key={group.id} value={group.id}>{group.name}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                导入数据
              </Button>
              <Button onClick={() => setCSVModalVisible(false)}>
                取消
              </Button>
              <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>
                下载模板
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 网络格式示例模态框 */}
      <Modal
        title="网络范围格式示例"
        open={examplesModalVisible}
        onCancel={() => setExamplesModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setExamplesModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={700}
      >
        {networkExamples && (
          <div>
            <Title level={4}>CIDR格式</Title>
            <Paragraph>{networkExamples.description.cidr}</Paragraph>
            <ul>
              {networkExamples.cidr_examples.map((example, index) => (
                <li key={index}><Text code>{example}</Text></li>
              ))}
            </ul>
            
            <Divider />
            
            <Title level={4}>IP范围格式</Title>
            <Paragraph>{networkExamples.description.range}</Paragraph>
            <ul>
              {networkExamples.range_examples.map((example, index) => (
                <li key={index}><Text code>{example}</Text></li>
              ))}
            </ul>
            
            <Divider />
            
            <Title level={4}>逗号分隔示例</Title>
            <Paragraph>{networkExamples.description.single}</Paragraph>
            <ul>
              {networkExamples.single_ip_examples.map((example, index) => (
                <li key={index}><Text code>{example}</Text></li>
              ))}
            </ul>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default DeviceDiscovery;