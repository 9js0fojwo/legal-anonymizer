#!/usr/bin/env python3
"""
回归测试运行器 - 验证脱敏检测的正确性

用法:
    python test/runner.py                    # 运行所有测试
    python test/runner.py --verbose          # 显示每个测试的所有检测结果
    python test/runner.py --fail-only        # 只显示失败的测试
    python test/runner.py cases/xxx.json     # 运行单个测试文件

测试用例格式（test/cases/*.json）:
    {
      "name": "描述这个测试覆盖的场景",
      "text": "要分析的文本片段（50-300字即可，不必是完整文书）",
      "must_detect": [
        {"text": "张三", "type": "person"},
        {"text": "北京示例科技有限公司", "type": "company"}
      ],
      "must_not_detect": [
        {"text": "汉族", "type": "person"},
        {"text": "有限公司", "type": "company"}
      ]
    }
"""

import json
import sys
from pathlib import Path

# 确保从项目根目录找到模块
sys.path.insert(0, str(Path(__file__).parent.parent))
from anonymizer import LegalAnonymizer


def run_case(case: dict, anonymizer: LegalAnonymizer, verbose: bool = False) -> tuple[bool, list[str]]:
    """
    运行单个测试用例

    Returns:
        (passed, error_messages)
    """
    text = case.get('text', '')
    analysis = anonymizer.analyze_text(text)

    # 构建扁平化的检测集合：{(text, type), ...}
    detected = set()
    for etype, items in analysis.get('findings', {}).items():
        for item in items:
            detected.add((item, etype))

    errors = []

    # 检查 must_detect
    for expected in case.get('must_detect', []):
        if (expected['text'], expected['type']) not in detected:
            errors.append(f"  漏报: '{expected['text']}' 类型={expected['type']}")

    # 检查 must_not_detect
    for forbidden in case.get('must_not_detect', []):
        if (forbidden['text'], forbidden['type']) in detected:
            errors.append(f"  误报: '{forbidden['text']}' 类型={forbidden['type']}")

    if verbose:
        print(f"    检测到的全部实体:")
        for etype, items in sorted(analysis.get('findings', {}).items()):
            for item in items:
                print(f"      [{etype}] {item}")

    return (len(errors) == 0), errors


def run_all(case_files: list[Path], fail_only: bool = False, verbose: bool = False) -> bool:
    anonymizer = LegalAnonymizer()
    passed = 0
    failed = 0
    total = 0

    for case_file in sorted(case_files):
        with open(case_file, encoding='utf-8') as f:
            try:
                cases = json.load(f)
            except json.JSONDecodeError as e:
                print(f"  JSON解析错误 {case_file.name}: {e}")
                continue

        # 支持单个用例（dict）或用例列表（list）
        if isinstance(cases, dict):
            cases = [cases]

        for case in cases:
            total += 1
            name = case.get('name', case_file.stem)
            ok, errors = run_case(case, anonymizer, verbose=verbose)

            if ok:
                passed += 1
                if not fail_only:
                    print(f"  ✓ {name}")
                if verbose:
                    print()
            else:
                failed += 1
                print(f"  ✗ {name}")
                for err in errors:
                    print(err)
                if verbose:
                    print()

    print()
    status = "全部通过" if failed == 0 else f"{failed} 个失败"
    print(f"结果: {passed}/{total} 通过  {status}")
    return failed == 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description='法律脱敏回归测试')
    parser.add_argument('files', nargs='*', help='指定测试文件（默认运行 test/cases/*.json）')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示所有检测结果')
    parser.add_argument('--fail-only', action='store_true', help='只显示失败的测试')
    args = parser.parse_args()

    cases_dir = Path(__file__).parent / 'cases'

    if args.files:
        case_files = [Path(f) for f in args.files]
    else:
        case_files = list(cases_dir.glob('*.json'))

    if not case_files:
        print(f"未找到测试用例文件（{cases_dir}/*.json）")
        sys.exit(1)

    print(f"运行 {len(case_files)} 个测试文件...\n")
    ok = run_all(case_files, fail_only=args.fail_only, verbose=args.verbose)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
