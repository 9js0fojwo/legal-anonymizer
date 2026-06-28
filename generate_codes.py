#!/usr/bin/env python3
"""
激活码生成器 — 仅供卖家使用！
用法: python generate_codes.py 10
生成 10 个激活码
"""

import sys
from activation import generate_code

def main():
    if len(sys.argv) < 2:
        count = 10
    else:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print("用法: python generate_codes.py <数量>")
            sys.exit(1)

    if count < 1 or count > 500:
        print("数量范围: 1-500")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"  Generated {count} activation codes")
    print(f"{'='*50}\n")

    codes = []
    for i in range(1, count + 1):
        # 前缀不含横杠，确保最终格式为 4 段
        prefix = f"LEGAL{i:04d}"
        code = generate_code(prefix)
        codes.append(code)
        print(f"  [{i:3d}]  {code}")

    print(f"\n{'='*50}")
    print(f"  Total: {count} codes, 199 CNY each")
    print(f"{'='*50}\n")

    # Save to file
    filename = "activation_codes.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Legal Anonymizer - Professional Edition Activation Codes\n")
        f.write(f"Generated: {__import__('datetime').datetime.now().isoformat()}\n")
        f.write(f"Count: {count}\n")
        f.write(f"Price: 199 CNY each\n")
        f.write(f"{'='*50}\n\n")
        for i, code in enumerate(codes, 1):
            f.write(f"[{i:3d}]  {code}  (unsold)\n")

    print(f"Saved to: {filename}")

if __name__ == "__main__":
    main()
