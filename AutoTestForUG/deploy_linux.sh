#!/bin/bash

# SIP自动化测试平台Linux服务器部署脚本
# 用于在Linux服务器上快速部署SIP自动化测试平台

set -e  # 遇到错误时退出

echo "开始部署SIP自动化测试平台..."

# 检查是否为root用户或具有sudo权限
if [[ $EUID -eq 0 ]]; then
   echo "警告: 请勿以root用户运行此脚本"
   exit 1
fi

# 检测Linux发行版
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$NAME
        VERSION=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        DISTRO=$(lsb_release -si)
        VERSION=$(lsb_release -sr)
    else
        DISTRO=$(uname -s)
        VERSION=$(uname -r)
    fi
}

# 安装系统依赖
install_system_deps() {
    echo "检测Linux发行版..."
    detect_distro
    echo "发现系统: $DISTRO $VERSION"
    
    case $DISTRO in
        *Ubuntu*|*Debian*)
            echo "安装Ubuntu/Debian系统依赖..."
            sudo apt-get update
            sudo apt-get install -y sipp libpjsua2-dev python3 python3-pip python3-dev build-essential net-tools
            ;;
        *CentOS*|*Red*|*Fedora*|*Oracle*)
            echo "安装CentOS/RHEL/Fedora系统依赖..."
            sudo yum update -y
            sudo yum install -y epel-release
            sudo yum install -y sipp libpjsua2-dev python3 python3-pip python3-devel gcc gcc-c++ net-tools
            ;;
        *SUSE*|*openSUSE*)
            echo "安装SUSE/openSUSE系统依赖..."
            sudo zypper refresh
            sudo zypper install -y sipp libpjsua2-dev python3 python3-pip python3-devel gcc gcc-c++ net-tools
            ;;
        *)
            echo "未识别的Linux发行版: $DISTRO"
            echo "请手动安装以下依赖：sipp, libpjsua2-dev, python3, python3-pip, python3-dev, build-essential"
            exit 1
            ;;
    esac
}

# 安装Python依赖
install_python_deps() {
    echo "安装Python依赖..."
    
    # 检查是否安装了poetry
    if command -v poetry &> /dev/null; then
        echo "使用poetry安装依赖..."
        poetry install
    else
        echo "poetry未安装，使用pip安装依赖..."
        if [ -f "pyproject.toml" ]; then
            pip3 install -e .
        elif [ -f "requirements.txt" ]; then
            pip3 install -r requirements.txt
        else
            echo "未找到依赖文件"
            exit 1
        fi
    fi
}

# 配置系统参数
configure_system() {
    echo "配置系统参数..."
    
    # 增加文件描述符限制
    echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
    echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
    
    # 配置网络参数以支持大量并发连接
    echo "net.core.somaxconn = 65535" | sudo tee -a /etc/sysctl.conf
    echo "net.ipv4.ip_local_port_range = 1024 65535" | sudo tee -a /etc/sysctl.conf
    echo "net.ipv4.tcp_fin_timeout = 30" | sudo tee -a /etc/sysctl.conf
    echo "net.ipv4.tcp_keepalive_time = 1200" | sudo tee -a /etc/sysctl.conf
    echo "net.ipv4.tcp_tw_reuse = 1" | sudo tee -a /etc/sysctl.conf
    echo "net.ipv4.tcp_max_syn_backlog = 8192" | sudo tee -a /etc/sysctl.conf
    
    # 应用系统参数
    sudo sysctl -p
}

# 创建日志目录
setup_logging() {
    echo "设置日志目录..."
    mkdir -p logs
    mkdir -p reports
    mkdir -p config
    touch logs/sip_test.log
}

# 主部署流程
main() {
    echo "开始SIP自动化测试平台部署..."
    
    # 检查当前目录
    if [ ! -f "pyproject.toml" ] && [ ! -f "requirements.txt" ]; then
        echo "错误: 未在项目根目录中运行脚本"
        exit 1
    fi
    
    # 安装系统依赖
    install_system_deps
    
    # 安装Python依赖
    install_python_deps
    
    # 配置系统参数
    configure_system
    
    # 设置日志目录
    setup_logging
    
    echo "部署完成!"
    echo ""
    echo "使用方法:"
    echo "  python3 -m AutoTestForUG.main --test-type all"
    echo ""
    echo "查看可用测试类型:"
    echo "  python3 -m AutoTestForUG.main --help"
}

# 执行主函数
main "$@"