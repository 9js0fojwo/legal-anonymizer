#!/usr/bin/env python3
"""
快速开始示例 - 法律文档脱敏工具
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from anonymizer import LegalAnonymizer


def example_1_basic_text():
    """示例1: 基本文本脱敏"""
    print("=" * 60)
    print("示例1: 基本文本脱敏")
    print("=" * 60)

    anonymizer = LegalAnonymizer()

    text = """
张三是北京示例科技有限公司的法定代表人，
他的手机号是13800001111，身份证号是110101199001011234，
邮箱是zhangsan@example.com。
    """.strip()

    print("\n原始文本:")
    print("-" * 60)
    print(text)

    anonymized, mapping = anonymizer.anonymize_text(text)

    print("\n\n脱敏后:")
    print("-" * 60)
    print(anonymized)

    print("\n\n映射表:")
    print("-" * 60)
    for placeholder, info in mapping.items():
        print(f"{placeholder} -> {info['original']} ({info['type']})")

    print()


def example_2_custom_entities():
    """示例2: 使用自定义实体"""
    print("=" * 60)
    print("示例2: 使用自定义实体")
    print("=" * 60)

    anonymizer = LegalAnonymizer()

    # 添加自定义实体
    anonymizer.add_custom_entity("person", "张三")
    anonymizer.add_custom_entity("person", "李四")
    anonymizer.add_custom_entity("company", "北京示例科技有限公司")
    anonymizer.add_custom_entity("company", "示例科技")
    anonymizer.add_custom_entity("address", "北京市海淀区中关村大街1号")
    anonymizer.add_custom_entity("law_firm", "北京市某某律师事务所")

    text = """
张三和李四代表北京示例科技有限公司（示例科技），
于2026年2月27日在北京市海淀区中关村大街1号
与北京市某某律师事务所签订了合同。
    """.strip()

    print("\n原始文本:")
    print("-" * 60)
    print(text)

    anonymized, mapping = anonymizer.anonymize_text(text)

    print("\n\n脱敏后:")
    print("-" * 60)
    print(anonymized)

    print()


def example_3_partial_masking():
    """示例3: 部分掩码策略"""
    print("=" * 60)
    print("示例3: 部分掩码策略（保留部分信息）")
    print("=" * 60)

    anonymizer = LegalAnonymizer()

    # 设置部分掩码策略
    anonymizer.set_mask_strategy("id_card", "partial")
    anonymizer.set_mask_strategy("phone", "partial")
    anonymizer.set_mask_strategy("email", "partial")
    anonymizer.set_mask_strategy("bank_account", "partial")

    text = """
身份证号：110101197001011234
手机号：13812345678
邮箱：zhangsan@example.com
银行卡号：6222021234567890123
    """.strip()

    print("\n原始文本:")
    print("-" * 60)
    print(text)

    anonymized, mapping = anonymizer.anonymize_text(text)

    print("\n\n脱敏后（部分掩码）:")
    print("-" * 60)
    print(anonymized)

    print()


def example_4_analyze():
    """示例4: 分析文档（不实际脱敏）"""
    print("=" * 60)
    print("示例4: 分析文档中的敏感信息")
    print("=" * 60)

    anonymizer = LegalAnonymizer()

    text = """
张三，身份证号110101199001011234，电话13800001111，
任职于北京示例科技有限公司（统一社会信用代码：91110000000000000X），
地址：北京市海淀区中关村大街1号，
邮箱：zhangsan@example.com，网址：http://www.example.com。
    """.strip()

    analysis = anonymizer.analyze_text(text)

    print(f"\n发现 {analysis['total_findings']} 处敏感信息")
    print(f"涉及 {analysis['type_count']} 种类型\n")

    for entity_type, examples in analysis['findings'].items():
        print(f"【{entity_type}】({len(examples)} 个):")
        for example in examples:
            print(f"  - {example}")
        print()


def example_5_file_processing():
    """示例5: 文件处理"""
    print("=" * 60)
    print("示例5: 文件处理")
    print("=" * 60)

    sample_file = Path(__file__).parent / "sample.txt"

    if not sample_file.exists():
        print(f"示例文件不存在: {sample_file}")
        return

    anonymizer = LegalAnonymizer()

    # 添加自定义实体
    entities_file = Path(__file__).parent / "sample_entities.json"
    anonymizer.load_entities_from_file(str(entities_file))

    # 分析文件
    print("\n[1/3] 分析文件...")
    analysis_result = anonymizer.analyze_file(str(sample_file))

    if 'error' in analysis_result:
        print(f"错误: {analysis_result['error']}")
        return

    analysis = analysis_result['result']['analysis']
    print(f"  发现 {analysis['total_findings']} 处敏感信息")

    # 脱敏文件
    print("\n[2/3] 脱敏文件...")
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # 先使用占位符策略
    result = anonymizer.anonymize_file(
        str(sample_file),
        str(output_dir / "sample_anonymized.txt"),
        output_format="txt",
        save_mapping=True
    )

    if 'error' in result:
        print(f"错误: {result['error']}")
        return

    r = result['result']
    print(f"  替换了 {r['replacements_made']} 处")

    # 再使用部分掩码策略
    print("\n[3/3] 使用部分掩码策略...")
    anonymizer.reset()
    anonymizer.load_entities_from_file(str(entities_file))

    # 设置部分掩码
    partial_types = ['id_card', 'phone', 'fax', 'toll_free', 'bank_account',
                   'email', 'passport', 'credit_code', 'license_plate']
    for etype in partial_types:
        anonymizer.set_mask_strategy(etype, "partial")

    result2 = anonymizer.anonymize_file(
        str(sample_file),
        str(output_dir / "sample_partial_masked.txt"),
        output_format="txt",
        save_mapping=True
    )

    print("\n完成！输出文件:")
    print(f"  - {output_dir / 'sample_anonymized.txt'}")
    print(f"  - {output_dir / 'sample_partial_masked.txt'}")
    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("法律文档脱敏工具 - 快速开始示例")
    print("=" * 60)

    examples = [
        ("基本文本脱敏", example_1_basic_text),
        ("自定义实体", example_2_custom_entities),
        ("部分掩码策略", example_3_partial_masking),
        ("分析文档", example_4_analyze),
        ("文件处理", example_5_file_processing),
    ]

    for i, (name, func) in enumerate(examples, 1):
        print(f"\n\n\n[{i}/{len(examples)}] {name}")
        try:
            func()
        except Exception as e:
            print(f"示例执行出错: {e}")
            import traceback
            traceback.print_exc()

        print()
        input("按 Enter 继续下一个示例...")

    print("\n" + "=" * 60)
    print("所有示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
