#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel配置管理模块使用示例
展示如何使用ExcelConfigManager类的各种功能
"""
from utils.excel_config_manager import ExcelConfigManager


def main():
    """主函数，演示Excel配置管理器的使用"""
    
    print("=== Excel配置管理器使用示例 ===\n")
    
    # 创建配置管理器实例
    manager = ExcelConfigManager("号码配置.xlsx")
    
    # 1. 加载配置
    print("1. 加载配置文件...")
    if manager.load_config():
        print("   ✓ 配置文件加载成功")
    else:
        print("   ✗ 配置文件加载失败")
        return
    
    # 2. 获取所有账号
    print("\n2. 获取所有账号...")
    all_accounts = manager.get_all_accounts()
    if all_accounts is not None:
        print(f"   总共有 {len(all_accounts)} 条配置记录")
    
    # 3. 根据账号查询
    print("\n3. 查询特定账号信息...")
    sample_account = "670100"  # 假设这是存在的账号
    account_info = manager.get_account_by_number(sample_account)
    if account_info:
        print(f"   账号 {sample_account} 信息:")
        print(f"   - FXS账号: {account_info['FXS账号']}")
        print(f"   - IP账号: {account_info['IP账号']}")
        print(f"   - 手机号码: {account_info['手机号码']}")
        print(f"   - 密码: {account_info['密码']}")
        print(f"   - 密码类型: {account_info['密码类型']}")
    else:
        print(f"   账号 {sample_account} 不存在")
    
    # 4. 获取FXS和IP账号
    print("\n4. 获取FXS和IP账号列表...")
    fxs_accounts = manager.get_fxs_accounts()
    ip_accounts = manager.get_ip_accounts()
    print(f"   FXS账号数量: {len(fxs_accounts)}")
    print(f"   IP账号数量: {len(ip_accounts)}")
    
    # 5. 根据密码类型筛选
    print("\n5. 根据密码类型筛选账号...")
    password_type_sample = "纯数字(长度4)"  # 示例密码类型
    typed_accounts = manager.get_accounts_by_password_type(password_type_sample)
    print(f"   密码类型为 '{password_type_sample}' 的账号数量: {len(typed_accounts)}")
    
    # 6. 根据账号范围筛选
    print("\n6. 根据账号范围筛选...")
    ranged_accounts = manager.get_accounts_by_range(670100, 670110)
    print(f"   账号范围 670100-670110 内的账号数量: {len(ranged_accounts)}")
    
    # 7. 根据条件筛选
    print("\n7. 根据自定义条件筛选...")
    def custom_condition(account):
        return "数字" in account['密码类型']  # 密码类型包含"数字"的账号
    
    conditional_accounts = manager.get_accounts_by_condition(custom_condition)
    print(f"   满足自定义条件的账号数量: {len(conditional_accounts)}")
    
    # 8. 更新账号密码
    print("\n8. 更新账号密码...")
    update_result = manager.update_account_password(sample_account, "new_password_123", "更新测试")
    if update_result:
        print(f"   账号 {sample_account} 密码更新成功")
        # 验证更新
        updated_info = manager.get_account_by_number(sample_account)
        print(f"   新密码: {updated_info['密码']}")
    else:
        print(f"   账号 {sample_account} 密码更新失败")
    
    # 9. 验证配置数据
    print("\n9. 验证配置数据...")
    validation_result = manager.validate_config_data()
    print(f"   配置有效性: {'✓ 有效' if validation_result['valid'] else '✗ 无效'}")
    print(f"   总记录数: {validation_result['stats']['total_records']}")
    print(f"   FXS账号数: {validation_result['stats']['fxs_accounts']}")
    print(f"   IP账号数: {validation_result['stats']['ip_accounts']}")
    
    # 10. 备份配置
    print("\n10. 备份配置文件...")
    try:
        backup_path = manager.backup_config()
        print(f"   ✓ 配置已备份至: {backup_path}")
    except Exception as e:
        print(f"   ✗ 备份失败: {e}")
    
    # 11. 列出备份文件
    print("\n11. 列出所有备份文件...")
    backups = manager.list_backups()
    for i, backup in enumerate(backups[:5]):  # 只显示前5个
        print(f"   {i+1}. {backup}")
    if len(backups) > 5:
        print(f"   ... 还有 {len(backups) - 5} 个备份文件")
    
    print("\n=== Excel配置管理器演示完成 ===")


if __name__ == "__main__":
    main()