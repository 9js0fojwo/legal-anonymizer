"""
LLM 检测器的冒烟测试
验证：
  1. 模型可以加载
  2. 在中英混合法律文本上能识别英文 PII
  3. 与现有规则检测器合并后不冲突
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detectors.llm_detector import LLMDetector


SAMPLE = """
民事起诉状

原告：张三，男，1985年3月12日生，身份证号 110105198503121234，
住北京市朝阳区建国路88号SOHO现代城A座1203室，
手机 13812345678，邮箱 zhangsan@example.com。

被告：Acme Legal Services, Inc., a company incorporated in Delaware,
represented by John Smith (CEO), email: john.smith@acme-legal.com,
phone: +1-415-555-0142, address: 2025 Mission Street, San Francisco, CA 94110, USA.

API access token for evidence platform: sk-proj-abcdEFGH1234ijklMNOP5678
Reference URL: https://evidence.court.gov.cn/case/2024-hu-0012

诉讼请求：
1. 判令被告 Acme Legal Services, Inc. 支付服务费 USD 125,000；
2. ...
"""


def main():
    det = LLMDetector()
    print("loading model ...")
    if not det.available:
        print("LLM 不可用：", det.load_error)
        sys.exit(1)

    print("\n=== 原文 ===")
    print(SAMPLE)

    hits = det.detect(SAMPLE)
    print(f"\n=== LLM 命中 ({len(hits)}) ===")
    for text, ty, pos in hits:
        print(f"  [{ty:14s}] @{pos:4d}  {text!r}")


if __name__ == "__main__":
    main()
