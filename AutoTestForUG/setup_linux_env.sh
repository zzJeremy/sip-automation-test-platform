#!/bin/bash
# Linux服务器环境初始化脚本

# 创建SIP测试专用用户
if ! id "sip-test" &>/dev/null; then
    sudo useradd -r -s /bin/false sip-test
    echo "创建用户 sip-test"
else
    echo "用户 sip-test 已存在"
fi

# 创建必要的目录并设置权限
sudo mkdir -p /opt/sip-auto-test
sudo mkdir -p /var/log/sip-auto-test
sudo mkdir -p /var/lib/sip-auto-test/results
sudo chown -R sip-test:sip-test /var/log/sip-auto-test
sudo chown -R sip-test:sip-test /var/lib/sip-auto-test

echo "Linux服务器环境初始化完成"
echo "请将项目文件复制到 /opt/sip-auto-test 目录"
echo "然后可以使用以下命令启动服务:"
echo "sudo systemctl enable sip-auto-test.service"
echo "sudo systemctl start sip-auto-test.service"