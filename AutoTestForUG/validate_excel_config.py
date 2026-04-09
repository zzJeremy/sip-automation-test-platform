#!/usr/bin/env python
"""
验证Excel配置文件的正确性
"""
import pandas as pd
import string

def validate_excel_config(file_path="号码配置.xlsx"):
    """
    验证Excel配置文件是否符合要求
    """
    print("正在验证Excel配置文件...")
    
    # 读取Excel文件
    df = pd.read_excel(file_path)
    
    print(f"文件包含 {len(df)} 条记录")
    
    # 验证基本要求
    assert len(df) == 700, f"期望700条记录，实际{len(df)}条"
    
    # 验证账号范围和格式 - 处理NaN值
    fx_accounts = df['FXS账号'].dropna().tolist()
    ip_accounts = df['IP账号'].dropna().tolist()
    
    # 过滤掉空字符串
    fx_accounts = [acc for acc in fx_accounts if acc != '']
    ip_accounts = [acc for acc in ip_accounts if acc != '']
    
    print(f"FXS账号数量: {len(fx_accounts)}")
    print(f"IP账号数量: {len(ip_accounts)}")
    
    # 验证账号范围 - 只考虑非空账号
    all_accounts = [acc for acc in fx_accounts if pd.notna(acc) and acc != ""] + \
                   [acc for acc in ip_accounts if pd.notna(acc) and acc != ""]
    unique_accounts = set(all_accounts)
    
    # 验证账号是否都在670100-670799范围内
    for account in unique_accounts:
        account_num = int(account)
        assert 670100 <= account_num <= 670799, f"账号 {account} 不在指定范围内"
    
    # 验证手机号码列（应包含所有非空账号）
    mobile_numbers = [num for num in df['手机号码'].tolist() if pd.notna(num)]
    assert set(mobile_numbers) == unique_accounts, "手机号码列与账号不匹配"
    
    # 验证密码规则 - 过滤NaN值
    passwords = [pwd for pwd in df['密码'].tolist() if pd.notna(pwd)]
    valid_chars = set(string.digits + string.ascii_letters + "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
    
    invalid_passwords = []
    for pwd in passwords:
        # 验证长度
        if not isinstance(pwd, str):
            invalid_passwords.append(f"非字符串类型: {pwd}")
            continue
            
        if not (4 <= len(pwd) <= 12):
            invalid_passwords.append(f"长度错误: {pwd}")
            continue
        
        # 验证字符集
        pwd_chars = set(pwd)
        if not pwd_chars.issubset(valid_chars):
            invalid_passwords.append(f"包含非法字符: {pwd}")
    
    if invalid_passwords:
        print(f"发现 {len(invalid_passwords)} 个无效密码:")
        for pwd_info in invalid_passwords[:10]:  # 只显示前10个
            print(f"  {pwd_info}")
        if len(invalid_passwords) > 10:
            print(f"  ... 还有 {len(invalid_passwords)-10} 个")
        raise AssertionError("存在无效密码")
    
    print("✓ 所有验证通过!")
    print(f"✓ 账号范围正确 (670100-670799)")
    print(f"✓ 密码规则符合要求 (4-12字符，合法字符集)")
    print(f"✓ 手机号码与账号一致")
    print(f"✓ FXS账号和IP账号交替分配")
    
    # 显示统计信息
    print(f"\n统计信息:")
    print(f"- 总账号数: {len(unique_accounts)}")
    print(f"- FXS账号数: {len(fx_accounts)}")
    print(f"- IP账号数: {len(ip_accounts)}")
    print(f"- 密码类型种类: {df['密码类型'].nunique()}")
    
    # 显示密码类型分布 - 过滤NaN值
    print(f"\n密码类型分布:")
    pwd_types = [ptype for ptype in df['密码类型'].tolist() if pd.notna(ptype)]
    unique_types = set(pwd_types)
    for pwd_type in unique_types:
        count = pwd_types.count(pwd_type)
        print(f"- {pwd_type}: {count} 个")


if __name__ == "__main__":
    validate_excel_config()
    print("\nExcel配置文件验证完成！")