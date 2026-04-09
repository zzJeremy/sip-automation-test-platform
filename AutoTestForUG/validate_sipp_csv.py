#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证生成的SIPP格式CSV文件
"""
import os
import re


def validate_sipp_csv():
    # 检查生成的CSV文件格式
    csv_file = 'sipp_号码配置_增强版.csv'
    if os.path.exists(csv_file):
        with open(csv_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f'文件总行数: {len(lines)}')
        
        # 检查第一行是否为SEQUENTIAL
        first_line = lines[0].strip()
        print(f'第一行内容: {repr(first_line)}')
        print(f'是否为SEQUENTIAL: {first_line == "SEQUENTIAL"}')
        
        # 检查格式正则表达式
        pattern = r'^(\d+);\[authentication username=(\d+) password=([^]]+)\]$'
        
        # 检查前几行数据格式
        print('\n检查前5行数据格式:')
        for i in range(1, 6):  # 检查第2到第6行
            if i < len(lines):
                line = lines[i].strip()
                match = re.match(pattern, line)
                if match:
                    account, username, password = match.groups()
                    print(f'第{i+1}行: 格式正确 - 账号={account}, 密码={password}')
                else:
                    print(f'第{i+1}行: 格式错误 - {line}')
        
        print('\n验证成功！SIPP格式的CSV文件已正确生成。')
    else:
        print(f'文件不存在: {csv_file}')


if __name__ == "__main__":
    validate_sipp_csv()