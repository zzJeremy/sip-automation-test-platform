#!/usr/bin/env python
"""
完整版密码测试用例生成器
输出完整的账号-密码对列表，用于被测设备配置
"""

import random
import string
from typing import List, Tuple

def generate_password_test_cases():
    """
    生成全面的密码测试用例，覆盖所有要求的字符类型组合
    """
    # 定义字符集
    digits = string.digits  # '0123456789'
    lowercase = string.ascii_lowercase  # 'abcdefghijklmnopqrstuvwxyz'
    uppercase = string.ascii_uppercase  # 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    punctuation = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"  # 英文标点符号
    
    all_chars = digits + lowercase + uppercase + punctuation
    
    test_cases = []
    
    # 1. 纯数字类型 (长度4和12)
    test_cases.extend(generate_char_type_cases(digits, "纯数字", [4, 12]))
    
    # 2. 纯小写字母类型 (长度4和12)
    test_cases.extend(generate_char_type_cases(lowercase, "纯小写字母", [4, 12]))
    
    # 3. 纯大写字母类型 (长度4和12)
    test_cases.extend(generate_char_type_cases(uppercase, "纯大写字母", [4, 12]))
    
    # 4. 纯大小写混合字母类型 (长度4和12)
    mixed_letters = lowercase + uppercase
    test_cases.extend(generate_char_type_cases(mixed_letters, "纯大小写混合字母", [4, 12]))
    
    # 5. 纯英文标点符号类型 (长度4和12)
    test_cases.extend(generate_char_type_cases(punctuation, "纯英文标点符号", [4, 12]))
    
    # 6. 数字+字母组合类型 (长度4和12)
    digit_letter = digits + lowercase + uppercase
    test_cases.extend(generate_char_type_cases(digit_letter, "数字+字母组合", [4, 12]))
    
    # 7. 数字+标点组合类型 (长度4和12)
    digit_punct = digits + punctuation
    test_cases.extend(generate_char_type_cases(digit_punct, "数字+标点组合", [4, 12]))
    
    # 8. 字母+标点组合类型 (长度4和12)
    letter_punct = lowercase + uppercase + punctuation
    test_cases.extend(generate_char_type_cases(letter_punct, "字母+标点组合", [4, 12]))
    
    # 9. 数字+字母+标点三者混合组合类型 (长度4和12)
    all_types = digits + lowercase + uppercase + punctuation
    test_cases.extend(generate_char_type_cases(all_types, "数字+字母+标点三者混合", [4, 12]))
    
    # 添加中间长度的测试用例（如6, 8, 10字符）
    # 纯数字类型 (中间长度)
    test_cases.extend(generate_char_type_cases(digits, "纯数字(中间长度)", [6, 8, 10]))
    
    # 纯小写字母类型 (中间长度)
    test_cases.extend(generate_char_type_cases(lowercase, "纯小写字母(中间长度)", [6, 8, 10]))
    
    # 纯大写字母类型 (中间长度)
    test_cases.extend(generate_char_type_cases(uppercase, "纯大写字母(中间长度)", [6, 8, 10]))
    
    # 纯大小写混合字母类型 (中间长度)
    test_cases.extend(generate_char_type_cases(mixed_letters, "纯大小写混合字母(中间长度)", [6, 8, 10]))
    
    # 纯英文标点符号类型 (中间长度)
    test_cases.extend(generate_char_type_cases(punctuation, "纯英文标点符号(中间长度)", [6, 8, 10]))
    
    # 数字+字母组合类型 (中间长度)
    test_cases.extend(generate_char_type_cases(digit_letter, "数字+字母组合(中间长度)", [6, 8, 10]))
    
    # 数字+标点组合类型 (中间长度)
    test_cases.extend(generate_char_type_cases(digit_punct, "数字+标点组合(中间长度)", [6, 8, 10]))
    
    # 字母+标点组合类型 (中间长度)
    test_cases.extend(generate_char_type_cases(letter_punct, "字母+标点组合(中间长度)", [6, 8, 10]))
    
    # 数字+字母+标点三者混合组合类型 (中间长度)
    test_cases.extend(generate_char_type_cases(all_types, "数字+字母+标点三者混合(中间长度)", [6, 8, 10]))
    
    # 为了确保有足够的样本，添加更多样例
    for _ in range(5):  # 每种类型再添加5个随机样本
        # 纯数字类型 (随机长度4-12)
        test_cases.extend(generate_char_type_cases(digits, "纯数字(随机)", [random.randint(4, 12)]))
        
        # 纯小写字母类型 (随机长度4-12)
        test_cases.extend(generate_char_type_cases(lowercase, "纯小写字母(随机)", [random.randint(4, 12)]))
        
        # 纯大写字母类型 (随机长度4-12)
        test_cases.extend(generate_char_type_cases(uppercase, "纯大写字母(随机)", [random.randint(4, 12)]))
        
        # 纯大小写混合字母类型 (随机长度4-12)
        test_cases.extend(generate_char_type_cases(mixed_letters, "纯大小写混合字母(随机)", [random.randint(4, 12)]))
        
        # 纯英文标点符号类型 (随机长度4-12)
        test_cases.extend(generate_char_type_cases(punctuation, "纯英文标点符号(随机)", [random.randint(4, 12)]))
        
        # 数字+字母组合类型 (随机长度4-12)
        test_cases.extend(generate_char_type_cases(digit_letter, "数字+字母组合(随机)", [random.randint(4, 12)]))
        
        # 数字+标点组合类型 (随机长度4-12)
        test_cases.extend(generate_char_type_cases(digit_punct, "数字+标点组合(随机)", [random.randint(4, 12)]))
        
        # 字母+标点组合类型 (随机长度4-12)
        test_cases.extend(generate_char_type_cases(letter_punct, "字母+标点组合(随机)", [random.randint(4, 12)]))
        
        # 数字+字母+标点三者混合组合类型 (随机长度4-12)
        test_cases.extend(generate_char_type_cases(all_types, "数字+字母+标点三者混合(随机)", [random.randint(4, 12)]))
    
    return test_cases

def generate_char_type_cases(char_set: str, description: str, lengths: List[int]) -> List[Tuple[str, str]]:
    """
    为特定字符类型和长度生成测试用例
    """
    cases = []
    for length in lengths:
        # 确保密码包含该类型的所有必要字符类型
        if description.startswith("纯数字"):
            password = ''.join(random.choice(string.digits) for _ in range(length))
        elif description.startswith("纯小写字母"):
            password = ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
        elif description.startswith("纯大写字母"):
            password = ''.join(random.choice(string.ascii_uppercase) for _ in range(length))
        elif description.startswith("纯大小写混合字母"):
            password = ''.join(random.choice(string.ascii_letters) for _ in range(length))
        elif description.startswith("纯英文标点符号"):
            password = ''.join(random.choice("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~") for _ in range(length))
        elif description.startswith("数字+字母组合"):
            # 至少包含一个数字和一个字母
            password = ensure_char_types([string.digits, string.ascii_letters], length)
        elif description.startswith("数字+标点组合"):
            # 至少包含一个数字和一个标点符号
            password = ensure_char_types([string.digits, "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"], length)
        elif description.startswith("字母+标点组合"):
            # 至少包含一个小写字母、大写字母和一个标点符号
            password = ensure_char_types([string.ascii_lowercase, string.ascii_uppercase, "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"], length)
        elif description.startswith("数字+字母+标点三者混合"):
            # 至少包含数字、字母和标点符号
            password = ensure_char_types([string.digits, string.ascii_letters, "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"], length)
        else:
            password = ''.join(random.choice(char_set) for _ in range(length))
        
        cases.append((description, password))
    
    return cases

def ensure_char_types(type_lists: List[str], total_length: int) -> str:
    """
    确保密码包含指定的字符类型
    """
    if total_length < len(type_lists):
        # 如果长度小于必需的字符类型数，则重复使用第一个字符集
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

def generate_account_password_pairs(start_account: int = 670000, end_account: int = 670099) -> List[Tuple[str, str, str]]:
    """
    生成账号-密码对，账号范围从start_account到end_account
    返回: List[Tuple[account, password, description]]
    """
    password_cases = generate_password_test_cases()
    
    account_password_pairs = []
    
    # 由于密码测试用例数量可能超过账号数量，我们循环使用密码
    for i in range(end_account - start_account + 1):
        account = str(start_account + i)
        password_idx = i % len(password_cases)
        desc, password = password_cases[password_idx]
        account_password_pairs.append((account, password, desc))
    
    return account_password_pairs

def save_full_test_cases(output_file: str = "full_password_test_cases.txt"):
    """
    保存完整的测试用例到文件
    """
    print("正在生成完整的密码测试用例...")
    account_password_pairs = generate_account_password_pairs(670000, 670099)  # 100个账号
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("用户注册密码测试用例完整清单\n")
        f.write("=" * 80 + "\n")
        f.write("测试目标: 验证系统对不同字符类型及长度组合密码的处理是否符合注册密码规则要求\n")
        f.write("账号范围: 670000 到 670099 (共100个账号)\n")
        f.write("密码规则: 4-12位，仅包含数字、英文字母和英文标点符号\n")
        f.write("覆盖9种字符类型组合: 纯数字、纯小写字母、纯大写字母、大小写混合字母、\n")
        f.write("                     纯标点符号、数字+字母、数字+标点、字母+标点、三者混合\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"{'序号':<8} {'账号':<10} {'密码':<15} {'类型':<25} {'长度'}\n")
        f.write("-" * 70 + "\n")
        
        for i, (acc, pwd, desc) in enumerate(account_password_pairs, 1):
            f.write(f"{i+669999:<8} {acc:<10} {pwd:<15} {desc:<25} {len(pwd)}\n")
        
        f.write(f"\n总计: {len(account_password_pairs)} 个账号-密码对测试用例\n")
        
        # 统计各类别分布
        type_counts = {}
        for _, _, desc in account_password_pairs:
            if desc in type_counts:
                type_counts[desc] += 1
            else:
                type_counts[desc] = 1
        
        f.write("\n各类别分布统计:\n")
        for desc, count in type_counts.items():
            f.write(f"- {desc}: {count} 个\n")
    
    print(f"完整测试用例已保存至: {output_file}")
    print(f"共生成 {len(account_password_pairs)} 个账号-密码对")

if __name__ == "__main__":
    save_full_test_cases()