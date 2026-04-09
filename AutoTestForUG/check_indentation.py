#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查web_app.py文件中的缩进问题
"""

def check_indentation():
    with open('e:/Project\Sip Auto Test\AutoTestForUG\web_interface\web_app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("检查第1860-1895行的缩进情况:")
    for i in range(1859, min(1895, len(lines))):  # 0-based indexing
        line = lines[i]
        stripped = line.lstrip()
        indent_size = len(line) - len(stripped)
        print(f"{i+1:4d}: {'|' + ' ' * (indent_size//2) + ('·' if indent_size % 2 == 1 else '') + ('  ' * (indent_size//2))}|{stripped.rstrip()}")

if __name__ == "__main__":
    check_indentation()