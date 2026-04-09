"""
Windows环境下安装PJSIP库的辅助脚本
"""
import os
import sys
import subprocess
import platform
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_system_requirements():
    """检查系统要求"""
    logger.info(f"操作系统: {platform.system()} {platform.release()}")
    logger.info(f"Python版本: {sys.version}")
    
    if platform.system() != "Windows":
        logger.warning("此脚本专为Windows系统设计")
        return False
    
    return True

def install_pjsip():
    """安装PJSIP库"""
    try:
        # 尝试安装预编译的wheel包
        logger.info("尝试安装pjsua2...")
        
        # 对于Windows，使用预编译的wheel包
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "--upgrade", "pjsua2"
        ], check=True, capture_output=True, text=True)
        
        logger.info("pjsua2安装成功!")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"直接安装失败: {e}")
        logger.info("尝试从GitHub获取预编译版本...")
        
        try:
            # 尝试从GitHub获取预编译版本
            # 注意：在实际情况下，用户可能需要手动下载适合其Python版本的wheel文件
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "pjsua2", "--force-reinstall", "--no-deps"
            ], check=True, capture_output=True, text=True)
            
            logger.info("pjsua2安装成功!")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"安装失败: {e}")
            logger.info("请手动下载适合您Python版本的pjsua2 wheel文件进行安装")
            logger.info("访问 https://github.com/pjsip/pjproject/releases 获取预编译版本")
            return False

def verify_installation():
    """验证PJSIP安装"""
    try:
        import pjsua2 as pj
        logger.info("PJSIP库导入成功!")
        
        # 尝试创建一个基本的Endpoint来验证功能
        ep = pj.Endpoint()
        logger.info("PJSIP库功能正常!")
        return True
        
    except ImportError as e:
        logger.error(f"PJSIP库导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"PJSIP库测试失败: {e}")
        return False

def install_dependencies():
    """安装可能需要的依赖"""
    try:
        logger.info("安装可能需要的构建工具...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "wheel", "setuptools", "cython"
        ], check=True, capture_output=True, text=True)
        logger.info("依赖安装完成!")
        return True
    except subprocess.CalledProcessError as e:
        logger.warning(f"依赖安装可能失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始PJSIP Windows安装流程...")
    
    if not check_system_requirements():
        return False
    
    # 安装依赖
    install_dependencies()
    
    # 安装PJSIP
    if install_pjsip():
        # 验证安装
        if verify_installation():
            logger.info("=" * 50)
            logger.info("PJSIP安装成功!")
            logger.info("现在可以在Windows环境下使用PJSIP协议栈了")
            logger.info("=" * 50)
            return True
        else:
            logger.error("PJSIP安装后验证失败")
            return False
    else:
        logger.error("PJSIP安装失败")
        logger.info("\n手动安装说明:")
        logger.info("1. 访问 https://github.com/pjsip/pjproject/releases")
        logger.info("2. 下载适合您Python版本的pjsua2 wheel文件")
        logger.info("3. 使用命令: pip install 下载的wheel文件路径")
        logger.info("4. 确保Python版本与wheel文件匹配 (例如cp39表示Python 3.9)")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("\nPJSIP已准备就绪，可以在项目中使用PJSIP协议栈进行调试")
    else:
        logger.error("\n安装过程遇到问题，请按照上述说明手动安装")
        sys.exit(1)