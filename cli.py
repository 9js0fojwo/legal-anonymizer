#!/usr/bin/env python3
"""
Legal Document Anonymizer - CLI Interface
法律文档脱敏工具 - 命令行接口

Usage:
    python cli.py anonymize input.pdf -o output.pdf
    python cli.py analyze input.docx
    python cli.py list-types
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional

from anonymizer import LegalAnonymizer


def load_entities_from_file(file_path: str) -> List[Dict]:
    """从文件加载自定义实体"""
    path = Path(file_path)
    if not path.exists():
        return []

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_result_summary(result: Dict, quiet: bool = False):
    """打印结果摘要"""
    if 'error' in result:
        if not quiet:
            print(f"❌ 错误: {result['error']}", file=sys.stderr)
        return

    r = result['result']

    if not quiet:
        print("\n" + "=" * 60)
        print("✅ 处理完成")
        print("=" * 60)

        analysis = r.get('analysis', {})
        print(f"\n📊 分析统计:")
        print(f"  发现的敏感信息类型: {analysis.get('type_count', 0)} 种")
        print(f"  总共发现: {analysis.get('total_findings', 0)} 处")

        print(f"\n🔒 脱敏统计:")
        print(f"  唯一实体数: {r.get('total_matched', 0)}")
        print(f"  替换次数: {r.get('replacements_made', 0)}")

        if 'output_txt' in r:
            print(f"  文本输出: {r['output_txt']}")
        if 'output_pdf' in r:
            print(f"  PDF输出: {r['output_pdf']}")
        if 'output_docx' in r:
            print(f"  Word输出: {r['output_docx']}")
        if 'output_md' in r:
            print(f"  Markdown输出: {r['output_md']}")
        if 'text_backup' in r:
            print(f"  文本备份: {r['text_backup']}")
        if 'mapping_file' in r:
            print(f"  映射表: {r['mapping_file']}")

        print("\n⚠️  注意: 映射表包含原始敏感信息，请妥善保管！")


def print_analysis_summary(result: Dict, quiet: bool = False, with_context: bool = False):
    """打印分析摘要"""
    if 'error' in result:
        if not quiet:
            print(f"❌ 错误: {result['error']}", file=sys.stderr)
        return

    r = result['result']
    analysis = r.get('analysis', {})
    findings = analysis.get('findings', {})

    if not quiet:
        print("\n" + "=" * 60)
        print("📋 文档敏感信息分析")
        print("=" * 60)

        print(f"\n📊 统计:")
        print(f"  敏感信息类型: {analysis.get('type_count', 0)} 种")
        print(f"  总共发现: {analysis.get('total_findings', 0)} 处")

        if findings:
            print(f"\n📝 详细发现:")
            for entity_type, examples in sorted(findings.items()):
                print(f"\n  【{entity_type}】({len(examples)} 个)")
                # 最多显示5个例子（有上下文时全部显示，更利于审查）
                limit = len(examples) if with_context else 3
                for i, example in enumerate(examples[:limit]):
                    if with_context and isinstance(example, dict):
                        # 有上下文模式：显示前后文
                        print(f"    ▸ {example['context'][:120]}")
                    else:
                        text_val = example if isinstance(example, str) else example.get('text', '')
                        if i == 2 and len(examples) > 3 and not with_context:
                            print(f"    - {text_val[:50]}… (还有 {len(examples)-2} 个)")
                        else:
                            print(f"    - {text_val[:60]}")


def print_supported_types(anonymizer: LegalAnonymizer):
    """打印支持的类型"""
    types = anonymizer.get_supported_types()

    print("\n" + "=" * 60)
    print("📋 支持的敏感信息类型")
    print("=" * 60)
    print()

    # 分组显示
    groups = {
        "身份证件类": ['id_card', 'passport', 'hk_macau_pass', 'taiwan_pass', 'military_id'],
        "企业/机构类": ['credit_code', 'org_code', 'tax_number'],
        "案件/合同类": ['case_number', 'contract_number', 'invoice_number'],
        "联系方式类": ['phone', 'fax', 'toll_free', 'email', 'website'],
        "网络标识类": ['ip_address', 'mac_address'],
        "金融类": ['bank_account', 'amount', 'price'],
        "车辆类": ['license_plate', 'vin'],
        "日期时间类": ['date', 'time', 'datetime'],
        "地址类": ['full_address', 'postal_code', 'house_number'],
        "证件/证书类": ['property_cert', 'permit_number'],
    }

    all_type_names = set(types.keys())
    shown_types = set()

    for group_name, group_types in groups.items():
        group_types_in_list = [t for t in group_types if t in types]
        if group_types_in_list:
            print(f"{group_name}:")
            for t in group_types_in_list:
                print(f"  • {t} - {types[t]}")
                shown_types.add(t)
            print()

    # 显示剩余类型
    remaining = all_type_names - shown_types
    if remaining:
        print("其他:")
        for t in sorted(remaining):
            print(f"  • {t} - {types.get(t, '')}")
        print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='法律文档脱敏工具 (环德律所) - 数据完全本地处理，保障隐私安全',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法 - 脱敏PDF文件
  %(prog)s anonymize input.pdf -o output.pdf

  # 脱敏文本文件
  %(prog)s anonymize input.txt -o output.txt

  # 脱敏Word文档
  %(prog)s anonymize input.docx -o output.docx

  # 使用自定义实体
  %(prog)s anonymize input.pdf -o output.pdf -e entities.json

  # 只脱敏指定字段
  %(prog)s anonymize input.pdf -o output.txt --only phone,email

  # 排除某些字段不脱敏
  %(prog)s anonymize input.pdf -o output.txt --exclude amount,date

  # 使用部分掩码策略（保留部分信息）
  %(prog)s anonymize input.pdf -o output.pdf --mask-strategy partial

  # 分析文档（不实际脱敏）
  %(prog)s analyze input.pdf

  # 列出所有支持的字段
  %(prog)s list-types
        """
    )

    subparsers = parser.add_subparsers(title='命令', dest='command', required=True)

    # ========== anonymize 命令 ==========
    anonymize_parser = subparsers.add_parser('anonymize', help='脱敏文件')
    anonymize_parser.add_argument('input', help='输入文件路径')
    anonymize_parser.add_argument('-o', '--output', help='输出文件路径')
    anonymize_parser.add_argument('-e', '--entities', help='自定义实体 JSON 文件路径')
    anonymize_parser.add_argument('-f', '--format',
                                     default='auto',
                                     help='输出格式：auto/txt/md/pdf/docx，或逗号分隔多格式（如 md,docx,pdf）')
    anonymize_parser.add_argument('--only', help='只脱敏指定字段，逗号分隔')
    anonymize_parser.add_argument('--exclude', help='排除指定字段，逗号分隔')
    anonymize_parser.add_argument('--mask-strategy', choices=['placeholder', 'partial'],
                                     help='掩码策略: placeholder(占位符) 或 partial(部分掩码)')
    anonymize_parser.add_argument('--all-strategy', choices=['placeholder', 'partial'],
                                     help='为所有类型设置掩码策略')
    anonymize_parser.add_argument('--ocr', action='store_true', help='对PDF使用OCR（处理扫描版）')
    anonymize_parser.add_argument('--ocr-engine', choices=['rapidocr', 'paddleocr', 'tesseract'],
                                     default='rapidocr',
                                     help='OCR 引擎：rapidocr（默认，快）| paddleocr（慢但对复杂排版更准）| tesseract')
    anonymize_parser.add_argument('--llm', action='store_true',
                                     help='启用 OpenAI privacy-filter (1.5B) 作为补充检测层 '
                                          '（首次使用会下载 ~2.6GB 模型；中文文档主要补英文实体）')
    anonymize_parser.add_argument('--cn-llm', action='store_true',
                                     help='启用 CLUENER 中文 NER (RoBERTa-base) 作为补充层 '
                                          '（~400MB；补规则漏掉的中文人名/公司/地址）')
    anonymize_parser.add_argument('--ollama', action='store_true',
                                     help='启用本地 Ollama 大模型作为第 5 补充层（无需额外下载，需本机运行 Ollama）')
    anonymize_parser.add_argument('--ollama-url', default=None, metavar='URL',
                                     help='Ollama 服务地址（默认 http://localhost:11434，'
                                          '或由 LEGAL_ANONYMIZER_OLLAMA_URL 环境变量指定）')
    anonymize_parser.add_argument('--ollama-model', default=None, metavar='MODEL',
                                     help='Ollama 模型名（默认 qwen2.5:7b，'
                                          '或由 LEGAL_ANONYMIZER_OLLAMA_MODEL 环境变量指定）')
    anonymize_parser.add_argument('--no-backup', action='store_true', help='不保存文本备份')
    anonymize_parser.add_argument('--no-mapping', action='store_true', help='不保存映射表')
    anonymize_parser.add_argument('-q', '--quiet', action='store_true', help='安静模式，只输出JSON')

    # ========== analyze 命令 ==========
    analyze_parser = subparsers.add_parser('analyze', help='分析文档敏感信息')
    analyze_parser.add_argument('input', help='输入文件路径')
    analyze_parser.add_argument('--only', help='只分析指定字段，逗号分隔')
    analyze_parser.add_argument('--exclude', help='排除指定字段，逗号分隔')
    analyze_parser.add_argument('--ocr', action='store_true', help='对PDF使用OCR')
    analyze_parser.add_argument('--ocr-engine', choices=['rapidocr', 'paddleocr', 'tesseract'],
                                default='rapidocr',
                                help='OCR 引擎：rapidocr（默认，快）| paddleocr（慢但精准）| tesseract')
    analyze_parser.add_argument('--llm', action='store_true',
                                help='启用 OpenAI privacy-filter 作为补充检测层')
    analyze_parser.add_argument('--cn-llm', action='store_true',
                                help='启用 CLUENER 中文 NER 作为补充层')
    analyze_parser.add_argument('--ollama', action='store_true',
                                help='启用本地 Ollama 大模型作为第 5 补充层')
    analyze_parser.add_argument('--ollama-url', default=None, metavar='URL',
                                help='Ollama 服务地址（默认 http://localhost:11434）')
    analyze_parser.add_argument('--ollama-model', default=None, metavar='MODEL',
                                help='Ollama 模型名（默认 qwen2.5:7b）')
    analyze_parser.add_argument('--context', action='store_true',
                                help='显示每个检测结果的前后文，便于判断是否误报')
    analyze_parser.add_argument('--context-window', type=int, default=40,
                                help='前后文窗口大小（字符数，默认40）')
    analyze_parser.add_argument('-q', '--quiet', action='store_true', help='安静模式，只输出JSON')

    # ========== list-types 命令 ==========
    list_types_parser = subparsers.add_parser('list-types', help='列出所有支持的字段')

    args = parser.parse_args()

    use_llm = getattr(args, 'llm', False)
    use_cn_llm = getattr(args, 'cn_llm', False)
    use_ollama = getattr(args, 'ollama', False)
    ollama_kw = {}
    if getattr(args, 'ollama_url', None):
        ollama_kw['base_url'] = args.ollama_url
    if getattr(args, 'ollama_model', None):
        ollama_kw['model'] = args.ollama_model
    anonymizer = LegalAnonymizer(
        use_llm=use_llm if use_llm else None,
        use_cn_llm=use_cn_llm if use_cn_llm else None,
        use_ollama=use_ollama if use_ollama else None,
        ollama_kwargs=ollama_kw or None,
    )

    if args.command == 'list-types':
        print_supported_types(anonymizer)
        return

    elif args.command == 'anonymize':
        # 加载自定义实体
        custom_entities = None
        if args.entities:
            custom_entities = load_entities_from_file(args.entities)

        # 解析字段过滤
        only_types = args.only.split(',') if args.only else None
        exclude_types = args.exclude.split(',') if args.exclude else None

        # 设置掩码策略
        if args.all_strategy:
            anonymizer.set_all_mask_strategy(args.all_strategy)
        elif args.mask_strategy:
            # 为常见类型设置部分掩码
            partial_types = ['id_card', 'phone', 'fax', 'toll_free', 'bank_account',
                           'email', 'passport', 'credit_code', 'license_plate']
            for etype in partial_types:
                anonymizer.set_mask_strategy(etype, args.mask_strategy)

        # 解析 --format：单格式字符串或逗号分隔多格式 list
        fmt_arg = args.format
        if fmt_arg and ',' in fmt_arg:
            fmt_arg = [s.strip() for s in fmt_arg.split(',') if s.strip()]

        # 执行脱敏
        result = anonymizer.anonymize_file(
            args.input,
            args.output,
            custom_entities=custom_entities,
            output_format=fmt_arg,
            only_types=only_types,
            exclude_types=exclude_types,
            use_ocr=args.ocr,
            ocr_engine=getattr(args, 'ocr_engine', 'rapidocr'),
            save_text_backup=not args.no_backup,
            save_mapping=not args.no_mapping
        )

        # 打印结果
        print_result_summary(result, args.quiet)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == 'analyze':
        only_types = args.only.split(',') if args.only else None
        exclude_types = args.exclude.split(',') if args.exclude else None

        result = anonymizer.analyze_file(
            args.input,
            only_types=only_types,
            exclude_types=exclude_types,
            use_ocr=args.ocr,
            ocr_engine=getattr(args, 'ocr_engine', 'rapidocr'),
            with_context=args.context,
            context_window=args.context_window
        )

        print_analysis_summary(result, args.quiet, with_context=args.context)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
