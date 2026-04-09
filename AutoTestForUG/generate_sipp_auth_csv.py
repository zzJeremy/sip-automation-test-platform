#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成SIPP格式的账号密码列表文件
格式：
第一行：SEQUENTIAL
从第二行开始：账号;[authentication username=账号 password=密码]
"""
import os


def generate_sipp_auth_file():
    """生成SIPP格式的账号密码列表文件"""
    
    # 从之前的XLSX文件获取账号密码数据
    # 或者根据之前定义的规则生成账号密码
    filename = "sipp_accounts_auth.csv"
    
    with open(filename, 'w', encoding='utf-8') as f:
        # 写入第一行：SEQUENTIAL
        f.write("SEQUENTIAL\n")
        
        # 生成账号密码数据（670100-670799）
        for account in range(670100, 670800):  # 670100 到 670799
            # 根据之前的规则，正常账号的密码是账号后四位
            password = f"{account % 10000:04d}"
            auth_line = f'{account};[authentication username={account} password={password}]\n'
            f.write(auth_line)
        
        # 添加异常账号数据（780001-780100）
        for account in range(780001, 780101):  # 780001 到 780100
            # 异常账号的密码使用简单递增模式
            password = f"{(account - 780000) * 123 % 10000:04d}"
            auth_line = f'{account};[authentication username={account} password={password}]\n'
            f.write(auth_line)
    
    print(f"SIPP格式账号密码列表已生成: {filename}")
    print(f"文件包含:")
    print(f"- 第1行: SEQUENTIAL")
    print(f"- 第2行到第701行: 670100-670799的账号密码（正常数据）")
    print(f"- 第702行到第801行: 780001-780100的账号密码（异常数据）")
    print(f"总计: 801 行数据")


def preview_file():
    """预览文件的前几行"""
    filename = "sipp_accounts_auth.csv"
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print("\n文件前5行预览:")
            for i, line in enumerate(lines[:5]):
                print(f"第{i+1}行: {line.strip()}")
            print(f"\n文件后5行预览:")
            for i, line in enumerate(lines[-5:], start=len(lines)-4):
                print(f"第{i}行: {line.strip()}")


if __name__ == "__main__":
    generate_sipp_auth_file()
    preview_file()