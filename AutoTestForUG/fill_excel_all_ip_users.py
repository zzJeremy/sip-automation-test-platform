#!/usr/bin/env python
"""
在真实的Excel模板中填写数据 - 全部设为IP用户
"""
import pandas as pd
import random
import string
from typing import List, Tuple


class PasswordGenerator:
    """密码生成器，用于生成符合要求的密码"""
    
    @staticmethod
    def generate_password_test_cases(count: int) -> List[Tuple[str, str]]:
        """
        生成指定数量的密码测试用例
        返回: List[Tuple[password, description]]
        """
        # 定义字符集
        digits = string.digits  # '0123456789'
        lowercase = string.ascii_lowercase  # 'abcdefghijklmnopqrstuvwxyz'
        uppercase = string.ascii_uppercase  # 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        punctuation = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"  # 英文标点符号
        
        test_cases = []
        
        # 生成9种类型的密码测试用例
        # 1. 纯数字类型 (长度4和12)
        for length in [4, 12]:
            password = ''.join(random.choice(digits) for _ in range(length))
            test_cases.append((password, f"纯数字(长度{length})"))
        
        # 2. 纯小写字母类型 (长度4和12)
        for length in [4, 12]:
            password = ''.join(random.choice(lowercase) for _ in range(length))
            test_cases.append((password, f"纯小写字母(长度{length})"))
        
        # 3. 纯大写字母类型 (长度4和12)
        for length in [4, 12]:
            password = ''.join(random.choice(uppercase) for _ in range(length))
            test_cases.append((password, f"纯大写字母(长度{length})"))
        
        # 4. 纯大小写混合字母类型 (长度4和12)
        for length in [4, 12]:
            password = ''.join(random.choice(lowercase + uppercase) for _ in range(length))
            test_cases.append((password, f"纯大小写混合字母(长度{length})"))
        
        # 5. 纯英文标点符号类型 (长度4和12)
        for length in [4, 12]:
            password = ''.join(random.choice(punctuation) for _ in range(length))
            test_cases.append((password, f"纯英文标点符号(长度{length})"))
        
        # 6. 数字+字母组合类型 (长度4和12)
        for length in [4, 12]:
            # 确保至少包含一个数字和一个字母
            password = PasswordGenerator._ensure_char_types([digits, lowercase + uppercase], length)
            test_cases.append((password, f"数字+字母组合(长度{length})"))
        
        # 7. 数字+标点组合类型 (长度4和12)
        for length in [4, 12]:
            # 确保至少包含一个数字和一个标点
            password = PasswordGenerator._ensure_char_types([digits, punctuation], length)
            test_cases.append((password, f"数字+标点组合(长度{length})"))
        
        # 8. 字母+标点组合类型 (长度4和12)
        for length in [4, 12]:
            # 确保至少包含一个字母和一个标点
            password = PasswordGenerator._ensure_char_types([lowercase + uppercase, punctuation], length)
            test_cases.append((password, f"字母+标点组合(长度{length})"))
        
        # 9. 数字+字母+标点三者混合组合类型 (长度4和12)
        for length in [4, 12]:
            # 确保至少包含数字、字母和标点
            password = PasswordGenerator._ensure_char_types([digits, lowercase + uppercase, punctuation], length)
            test_cases.append((password, f"数字+字母+标点三者混合(长度{length})"))
        
        # 添加中间长度的测试用例
        for length in [6, 8, 10]:
            # 纯数字
            password = ''.join(random.choice(digits) for _ in range(length))
            test_cases.append((password, f"纯数字(长度{length})"))
            
            # 纯小写字母
            password = ''.join(random.choice(lowercase) for _ in range(length))
            test_cases.append((password, f"纯小写字母(长度{length})"))
            
            # 纯大写字母
            password = ''.join(random.choice(uppercase) for _ in range(length))
            test_cases.append((password, f"纯大写字母(长度{length})"))
            
            # 纯大小写混合字母
            password = ''.join(random.choice(lowercase + uppercase) for _ in range(length))
            test_cases.append((password, f"纯大小写混合字母(长度{length})"))
            
            # 纯英文标点符号
            password = ''.join(random.choice(punctuation) for _ in range(length))
            test_cases.append((password, f"纯英文标点符号(长度{length})"))
            
            # 数字+字母组合
            password = PasswordGenerator._ensure_char_types([digits, lowercase + uppercase], length)
            test_cases.append((password, f"数字+字母组合(长度{length})"))
            
            # 数字+标点组合
            password = PasswordGenerator._ensure_char_types([digits, punctuation], length)
            test_cases.append((password, f"数字+标点组合(长度{length})"))
            
            # 字母+标点组合
            password = PasswordGenerator._ensure_char_types([lowercase + uppercase, punctuation], length)
            test_cases.append((password, f"字母+标点组合(长度{length})"))
            
            # 数字+字母+标点三者混合
            password = PasswordGenerator._ensure_char_types([digits, lowercase + uppercase, punctuation], length)
            test_cases.append((password, f"数字+字母+标点三者混合(长度{length})"))
        
        # 补充随机测试用例直到达到所需数量
        while len(test_cases) < count:
            length = random.randint(4, 12)
            char_set = digits + lowercase + uppercase + punctuation
            password = ''.join(random.choice(char_set) for _ in range(length))
            test_cases.append((password, f"随机密码(长度{length})"))
        
        return test_cases[:count]  # 确保返回正确的数量
    
    @staticmethod
    def _ensure_char_types(type_lists: List[str], total_length: int) -> str:
        """
        确保密码包含指定的字符类型
        """
        if total_length < len(type_lists):
            # 如果长度小于必需的字符类型数，则重复使用字符集
            password_chars = []
            for i in range(total_length):
                char_set = type_lists[i % len(type_lists)]
                password_chars.append(random.choice(char_set))
            return ''.join(password_chars)
        
        # 从每个字符集中选择至少一个字符
        password_chars = []
        for char_set in type_lists:
            password_chars.append(random.choice(char_set))
        
        # 填充剩余位置
        all_chars = ''.join(type_lists)
        for _ in range(total_length - len(type_lists)):
            password_chars.append(random.choice(all_chars))
        
        # 随机打乱顺序
        random.shuffle(password_chars)
        return ''.join(password_chars)


def fill_real_excel_template_all_ip(start_account: int = 670100, end_account: int = 670799, template_file: str = "号码配置.xlsx", output_file: str = "号码配置.xlsx"):
    """
    在真实的Excel模板中填写数据 - 全部设为IP用户
    """
    print(f"正在填写真实Excel模板（全部IP用户），账号范围 {start_account} 到 {end_account}...")
    
    # 计算账号总数
    total_accounts = end_account - start_account + 1
    print(f"总计需要填写 {total_accounts} 个账号")
    
    # 生成密码测试用例
    password_cases = PasswordGenerator.generate_password_test_cases(total_accounts)
    
    # 创建新的数据框
    columns = [
        '手机号码', 'FXS端口', '默认路由计划', '高级路由计划', '低级路由计划', 
        '绑定IP账号数量', '来显方式', '反极控制', '业务密码', '注册密码', 
        '号码业务', 'DID1', 'DID2', 'DID3', '彩铃', '用户类别（1-15）', 
        'FXS帐号', 'ip帐号', '短号', '号码闭塞(0-禁用,1-启用)', 
        '收号方式(0-DSP,1-SLIC)', '呼叫频度'
    ]
    
    # 创建新的数据框
    new_data = []
    
    for i in range(total_accounts):
        account = str(start_account + i)
        password_idx = i % len(password_cases)
        password, description = password_cases[password_idx]
        
        # 创建一行数据，所有账号都设为IP用户
        row_data = {
            '手机号码': account,  # 号码等于账号
            'FXS端口': '',  # 留空，因为全是IP用户
            '默认路由计划': '高级路由计划',  # 默认值
            '高级路由计划': '默认',  # 默认值
            '低级路由计划': '',  # 可以留空
            '绑定IP账号数量': 0,  # 默认值
            '来显方式': 0,  # 默认值
            '反极控制': 0,  # 默认值
            '业务密码': password,  # 生成的密码
            '注册密码': password,  # 生成的密码
            '号码业务': '',  # 可以留空
            'DID1': '',  # 可以留空
            'DID2': '',  # 可以留空
            'DID3': '',  # 可以留空
            '彩铃': 0,  # 默认值
            '用户类别（1-15）': 1,  # 默认值
            'FXS帐号': '',  # 全部设为IP用户，所以FXS帐号留空
            'ip帐号': account,   # 所有账号都填入IP帐号列
            '短号': '',  # 可以留空
            '号码闭塞(0-禁用,1-启用)': 0,  # 默认值
            '收号方式(0-DSP,1-SLIC)': 1,  # 默认值
            '呼叫频度': 0  # 默认值
        }
        
        new_data.append(row_data)
    
    # 创建新的DataFrame
    df_new = pd.DataFrame(new_data, columns=columns)
    
    # 保存到Excel
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_new.to_excel(writer, sheet_name='账号配置', index=False)
        
        # 获取工作表对象以设置列宽
        worksheet = writer.sheets['账号配置']
        
        # 设置列宽
        for col in worksheet.columns:
            max_length = 0
            column = col[0].column_letter  # 获取列字母
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # 最大宽度限制为50
            worksheet.column_dimensions[column].width = adjusted_width
    
    print(f"Excel模板已更新: {output_file}")
    print(f"文件包含 {len(df_new)} 条记录")
    
    # 显示前10条记录作为示例
    print("\n前10条记录预览:")
    for i in range(min(10, len(df_new))):
        row = df_new.iloc[i]
        fxs = row['FXS帐号'] if pd.notna(row['FXS帐号']) else ""
        ip = row['ip帐号'] if pd.notna(row['ip帐号']) else ""
        mobile = row['手机号码'] if pd.notna(row['手机号码']) else ""
        biz_pwd = row['业务密码'] if pd.notna(row['业务密码']) else ""
        reg_pwd = row['注册密码'] if pd.notna(row['注册密码']) else ""
        print(f"行{i+1}: FXS账号={fxs}, IP账号={ip}, 手机号码={mobile}, 业务密码={biz_pwd}, 注册密码={reg_pwd}")
    
    return len(df_new)


if __name__ == "__main__":
    # 在真实Excel模板中填写数据（全部IP用户）
    count = fill_real_excel_template_all_ip(670100, 670799, "号码配置.xlsx", "号码配置.xlsx")
    print(f"\nExcel模板填写完成！共填写 {count} 条记录，全部为IP用户")