"""
Legal Document Anonymizer - Main Class
法律文档脱敏器 - 核心类
"""

from typing import Dict, List, Tuple, Optional
from pathlib import Path

from detectors.pattern_detector import PatternDetector
from detectors.entity_detector import EntityDetector
from detectors.llm_detector import LLMDetector, is_llm_enabled_via_env, get_shared_detector
from detectors.cn_ner_detector import (
    CNNERDetector,
    get_shared_cn_detector,
    is_cn_llm_enabled_via_env,
)
from maskers.text_masker import TextMasker
from processors.file_processor import FileProcessor


class LegalAnonymizer:
    """法律文档脱敏器 - 主类"""

    def __init__(
        self,
        use_llm: Optional[bool] = None,
        use_cn_llm: Optional[bool] = None,
        llm_kwargs: Optional[Dict] = None,
        cn_llm_kwargs: Optional[Dict] = None,
    ):
        """
        Args:
            use_llm: 启用 OpenAI privacy-filter（英文 PII 为主）。None 读环境变量
                     LEGAL_ANONYMIZER_LLM；False 关闭。
            use_cn_llm: 启用 CLUENER 中文 NER（中文人名/公司/地址等规则盲区）。
                        None 读环境变量 LEGAL_ANONYMIZER_CN_LLM；False 关闭。
            llm_kwargs / cn_llm_kwargs: 分别透传给两个检测器
        """
        self.pattern_detector = PatternDetector()
        self.entity_detector = EntityDetector()
        self.masker = TextMasker()
        self.processor = FileProcessor()

        if use_llm is None:
            use_llm = is_llm_enabled_via_env()
        if use_cn_llm is None:
            use_cn_llm = is_cn_llm_enabled_via_env()
        self.use_llm = bool(use_llm)
        self.use_cn_llm = bool(use_cn_llm)

        self.llm_detector: Optional[LLMDetector] = None
        self.cn_ner_detector: Optional[CNNERDetector] = None
        if self.use_llm:
            self.llm_detector = get_shared_detector(**(llm_kwargs or {}))
        if self.use_cn_llm:
            self.cn_ner_detector = get_shared_cn_detector(**(cn_llm_kwargs or {}))

    def set_mask_strategy(self, entity_type: str, strategy: str):
        """
        设置指定类型的掩码策略

        Args:
            entity_type: 实体类型
            strategy: 'placeholder'（占位符）或 'partial'（部分掩码）
        """
        self.masker.set_strategy(entity_type, strategy)

    def set_all_mask_strategy(self, strategy: str):
        """
        设置所有类型的掩码策略

        Args:
            strategy: 'placeholder' 或 'partial'
        """
        self.masker.set_all_strategy(strategy)

    def add_custom_entity(self, entity_type: str, name: str):
        """
        添加自定义实体

        Args:
            entity_type: 实体类型
            name: 实体名称
        """
        self.entity_detector.add_entity(entity_type, name)

    def add_custom_entities(self, entities: List[Dict]):
        """
        批量添加自定义实体

        Args:
            entities: 实体列表 [{"type": "person", "name": "张三"}, ...]
        """
        self.entity_detector.add_entities(entities)

    def load_entities_from_file(self, file_path: str):
        """
        从JSON文件加载自定义实体

        Args:
            file_path: JSON文件路径
        """
        import json
        path = Path(file_path)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                entities = json.load(f)
                self.add_custom_entities(entities)

    def clear_custom_entities(self):
        """清空自定义实体"""
        self.entity_detector.clear()

    def _detect_all(self, text: str, only_types: List[str] = None, exclude_types: List[str] = None) -> List:
        """
        三层检测融合：
          1. 正则（PatternDetector） —— 结构化数据最稳，最高优先
          2. 规则实体（EntityDetector） —— 中文人名/公司等，上下文关键词驱动
          3. CN NER（CLUENER） —— 中文人名/公司盲区，并修正规则层常见错误
          4. OpenAI privacy-filter —— 英文 PII 和 secret

        冲突仲裁规则（仅在规则层和 CN NER 重叠时）：
          - 同一 span 上规则判 person 但 CN NER 判 company/institution → 采纳 CN NER
            （修复规则把公司名误判为人名等跨类错误）
          - person vs person 重叠时，采纳更长的 span
            （修复复姓人名的边界错切，让 LLM 完整 span 胜出）
          - 其它情况：规则优先，CN NER 丢弃

        OpenAI 层不参与仲裁，只补规则+CN NER 没覆盖的空位。

        Returns:
            合并后的实体列表 [(实体文本, 类型, 位置), ...]
        """
        pattern_entities = self.pattern_detector.detect(text, only_types, exclude_types)
        entity_entities = self.entity_detector.detect(text, only_types, exclude_types)
        self.masker.set_abbreviation_map(self.entity_detector.abbreviation_map)

        merged = pattern_entities + entity_entities

        # --- 第 3 层：CN NER 融合（带仲裁）---
        if self.use_cn_llm and self.cn_ner_detector is not None:
            cn_hits = self.cn_ner_detector.detect(text, only_types, exclude_types)
            merged = self._merge_cn_ner(merged, cn_hits)

        # --- 第 4 层：OpenAI privacy-filter（仅补空位）---
        if self.use_llm and self.llm_detector is not None:
            llm_entities = self.llm_detector.detect(text, only_types, exclude_types)
            occupied = [(p, p + len(t)) for t, _, p in merged]
            for t, ty, p in llm_entities:
                end = p + len(t)
                if any(p < oe and end > os_ for os_, oe in occupied):
                    continue
                merged.append((t, ty, p))
                occupied.append((p, end))

        # --- 第 5 步：同名全文一致性扩展 ---
        # 如果某个人名（如"张三"）在某处已被识别为 person，全文所有该姓名位置都补上
        # 仅针对人名和公司/机构名；避免泛地名/职位导致炸量
        merged = self._expand_same_name_occurrences(text, merged)

        return merged

    def _write_format(
        self,
        fmt: str,
        input_path: Path,
        output_path: Path,
        input_suffix: str,
        anonymized_content: str,
        use_ocr: bool,
    ) -> List[Tuple[str, str]]:
        """
        按目标格式输出一份文件。优先级：
          - fmt=docx 且源为 docx → 原地替换（完美保留格式）
          - fmt=pdf  且源为 pdf  → 原地 redact（保留布局/盖章）
          - 其它情况走 processor.write_file 用回退模板（仿宋/小四/1.5x）
        """
        fmt = (fmt or '').lower()
        target_path = output_path.with_suffix('.' + fmt) if fmt in ('md', 'pdf', 'docx', 'txt') else output_path

        # docx → docx 原地
        if fmt == 'docx' and input_suffix == '.docx' and not use_ocr:
            if self.processor.anonymize_docx_inplace(
                str(input_path), str(target_path), self.masker.mapping
            ):
                return [('output_docx', str(target_path))]
            # 失败回退
            return self.processor.write_file(anonymized_content, str(target_path), 'docx')

        # pdf → pdf 原地 redact
        if fmt == 'pdf' and input_suffix == '.pdf' and not use_ocr:
            if self.processor.anonymize_pdf_inplace(
                str(input_path), str(target_path), self.masker.mapping
            ):
                return [('output_pdf', str(target_path))]
            # 失败回退
            return self.processor.write_file(anonymized_content, str(target_path), 'pdf')

        # 其它：回退到模板输出
        return self.processor.write_file(anonymized_content, str(target_path), fmt or 'auto')

    @staticmethod
    def _expand_same_name_occurrences(text: str, entities: List) -> List:
        """
        对所有已识别的 person/company/institution，在全文补上其它出现位置。
        解决：CN NER 在部分上下文中漏检同名实体的问题。
        """
        EXPAND_TYPES = {"person", "company", "institution", "law_firm", "government", "court"}
        by_position = {(p, p + len(t)): (t, ty) for t, ty, p in entities}
        known_names = {}  # name -> type（取第一次出现的类型）
        for t, ty, p in entities:
            if ty in EXPAND_TYPES and len(t) >= 2:
                known_names.setdefault(t, ty)

        result = list(entities)
        existing_spans = [(p, p + len(t)) for t, _, p in entities]

        for name, ty in known_names.items():
            i = 0
            while True:
                idx = text.find(name, i)
                if idx == -1:
                    break
                end = idx + len(name)
                # 是否已存在重叠命中
                overlapped = any(idx < oe and end > os_ for os_, oe in existing_spans)
                if not overlapped:
                    result.append((name, ty, idx))
                    existing_spans.append((idx, end))
                i = idx + 1
        return result

    @staticmethod
    def _merge_cn_ner(rule_hits: List, cn_hits: List) -> List:
        """
        仲裁合并规则层和 CN NER 层的命中。返回合并后的列表。

        冲突处理（按优先级）：
          1. 规则.person ∩ CN_NER.(company|institution|government) → 采纳 CN NER，替换规则
          2. 规则.person ∩ CN_NER.person 且 CN NER 覆盖规则 → 采纳 CN NER（更长的 span）
          3. 其它重叠 → 丢弃 CN NER（规则优先）
          4. 不重叠 → 保留 CN NER
        """
        def span_overlaps(a_start, a_end, b_start, b_end):
            return a_start < b_end and b_start < a_end

        from detectors.cn_ner_detector import COMPOUND_SURNAMES

        def cn_wins(cn: Tuple[str, str, int], rule: Tuple[str, str, int]) -> bool:
            """给定一对重叠的 (cn_hit, rule_hit)，判断 CN NER 是否应该胜出"""
            t, ty, p = cn; end = p + len(t)
            rt, rty, rp = rule; rend = rp + len(rt)
            # a) person ↔ 组织类纠错（公司名被规则误判为 person → 修正为 company）
            if rty == "person" and ty in ("company", "institution", "government"):
                return True
            # b) person ↔ person：CN NER 以复姓开头 或 更长
            if rty == "person" and ty == "person":
                starts_with_compound = len(t) >= 3 and t[:2] in COMPOUND_SURNAMES
                if starts_with_compound or len(t) > len(rt):
                    return True
            # c) CN NER 完整地址包含规则的房间号/邮编碎片 → 采纳 CN NER
            if ty == "full_address" and rty in ("house_number", "postal_code", "full_address"):
                if p <= rp and end >= rend and len(t) > len(rt):
                    return True
            # d) CN NER 命中被规则 **同类型碎片**完全包含 → CN NER 胜出
            #    修复：规则贪婪匹配产出"动词+短公司名"这类垃圾碎片，把短公司名
            #    (CN NER) 的位置占住。CN NER 置信度 >= 0.8（默认阈值）已说明是真实体。
            COMPAT = {
                "company": {"company"},
                "institution": {"institution", "company"},
                "government": {"government"},
                "person": {"person"},
                "full_address": {"full_address", "house_number"},
            }
            if ty in COMPAT and rty in COMPAT[ty]:
                # rule 严格包含 cn，且 cn 长度占 rule 的一半以上（避免误判短片段）
                if rp <= p and rend >= end and len(rt) > len(t) and len(t) * 2 >= len(rt):
                    return True
            return False

        result = list(rule_hits)
        to_drop = set()

        for cn in cn_hits:
            t, ty, p = cn; end = p + len(t)
            overlapping = []
            for i, rule in enumerate(result):
                if i in to_drop:
                    continue
                rt, rty, rp = rule; rend = rp + len(rt)
                if span_overlaps(p, end, rp, rend):
                    overlapping.append((i, rule))

            if not overlapping:
                result.append(cn)
                continue

            # 对所有重叠项判断：只有全部判 CN NER 胜才采纳
            if all(cn_wins(cn, rule) for _, rule in overlapping):
                for i, _ in overlapping:
                    to_drop.add(i)
                result.append(cn)
            # 否则丢弃 CN NER 命中（规则优先）

        if to_drop:
            result = [x for i, x in enumerate(result) if i not in to_drop]
        return result

    def _build_analysis(self, all_entities: List, text: str = None, context_window: int = 0) -> Dict:
        """
        从检测结果构建分析报告

        Args:
            all_entities: 实体列表
            text: 原始文本（传入时附带上下文，否则只返回实体名）
            context_window: 上下文窗口大小（字符数），0 = 不附带上下文
        """
        findings = {}
        for entity_text, entity_type, pos in all_entities:
            if entity_type not in findings:
                findings[entity_type] = []

            if text and context_window > 0:
                ctx_before = text[max(0, pos - context_window):pos].replace('\n', ' ')
                ctx_after = text[pos + len(entity_text):pos + len(entity_text) + context_window].replace('\n', ' ')
                entry = {
                    "text": entity_text,
                    "context": f"…{ctx_before}【{entity_text}】{ctx_after}…"
                }
                if not any(e["text"] == entity_text for e in findings[entity_type]):
                    findings[entity_type].append(entry)
            else:
                if entity_text not in findings[entity_type]:
                    findings[entity_type].append(entity_text)

        return {
            "findings": findings,
            "total_findings": len(all_entities),
            "type_count": len(findings)
        }

    def anonymize_text(
        self,
        text: str,
        only_types: List[str] = None,
        exclude_types: List[str] = None
    ) -> Tuple[str, Dict]:
        """
        脱敏文本

        Args:
            text: 原始文本
            only_types: 只脱敏指定类型
            exclude_types: 排除指定类型

        Returns:
            (脱敏后文本, 详细映射信息)
        """
        self.masker.reset()
        all_entities = self._detect_all(text, only_types, exclude_types)
        anonymized_text, mapping = self.masker.mask_all(text, all_entities)
        return anonymized_text, mapping

    def analyze_text(
        self,
        text: str,
        only_types: List[str] = None,
        exclude_types: List[str] = None,
        with_context: bool = False,
        context_window: int = 40
    ) -> Dict:
        """
        分析文本中的敏感信息（不实际脱敏）

        Args:
            with_context: 是否在结果中附带前后文
            context_window: 上下文窗口大小（字符数），仅 with_context=True 时生效

        Returns:
            分析结果，with_context=True 时 findings 中每项为 {text, context} 字典
        """
        all_entities = self._detect_all(text, only_types, exclude_types)
        return self._build_analysis(
            all_entities,
            text=text if with_context else None,
            context_window=context_window if with_context else 0
        )

    def anonymize_file(
        self,
        input_path: str,
        output_path: str = None,
        custom_entities: List[Dict] = None,
        output_format=None,
        only_types: List[str] = None,
        exclude_types: List[str] = None,
        use_ocr: bool = False,
        ocr_engine: str = 'rapidocr',
        save_text_backup: bool = True,
        save_mapping: bool = True
    ) -> Dict:
        """
        脱敏文件

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            custom_entities: 自定义实体列表
            output_format: 输出格式。str='auto/txt/md/pdf/docx' 或 list 多格式同时输出
                           如 ['md','docx','pdf'] 会同时生成三份（推荐）。
                           None/'auto' 时按输出路径后缀推断。
            only_types: 只脱敏指定类型
            exclude_types: 排除指定类型
            use_ocr: 是否使用OCR处理扫描版PDF
            ocr_engine: OCR 引擎 'rapidocr'（默认）| 'paddleocr'（慢但精准）| 'tesseract'
            save_text_backup: 是否保存文本备份
            save_mapping: 是否保存映射表

        Returns:
            结果字典
        """
        input_path = Path(input_path)

        if not input_path.exists():
            return {"error": f"文件不存在: {input_path}"}

        # 添加自定义实体（先清除上次残留，避免跨调用污染）
        self.entity_detector.clear()
        if custom_entities:
            self.add_custom_entities(custom_entities)

        # 提取文本
        try:
            content = self.processor.extract_text(str(input_path), use_ocr=use_ocr, ocr_engine=ocr_engine)
        except Exception as e:
            return {"error": f"读取文件失败: {e}"}

        if not content.strip():
            return {"error": "文件内容为空"}

        # 一次检测，同时用于分析和脱敏（避免重复检测）
        self.masker.reset()
        all_entities = self._detect_all(content, only_types, exclude_types)
        analysis = self._build_analysis(all_entities)
        anonymized_content, detailed_mapping = self.masker.mask_all(content, all_entities)

        # 准备结果
        result_info = {
            "input_file": str(input_path),
            "analysis": analysis,
            "anonymized_content": anonymized_content,
            "mapping": detailed_mapping["mapping"],
            "total_matched": detailed_mapping["metadata"]["entity_count"],
            "replacements_made": detailed_mapping["metadata"]["replacements_made"],
            "replacement_log": detailed_mapping["replacement_log"]
        }

        # 保存输出
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            saved_files = []

            # 解析 output_format：支持 list（多格式）、str（单格式）、None（auto）
            input_suffix = input_path.suffix.lower()
            if output_format is None or output_format == 'auto':
                formats = [self.processor._guess_format(output_path)]
            elif isinstance(output_format, str):
                formats = [output_format]
            elif isinstance(output_format, (list, tuple)):
                formats = list(output_format)
            else:
                formats = [self.processor._guess_format(output_path)]

            # 逐格式生成
            for fmt in formats:
                main_files = self._write_format(
                    fmt=fmt,
                    input_path=input_path,
                    output_path=output_path,
                    input_suffix=input_suffix,
                    anonymized_content=anonymized_content,
                    use_ocr=use_ocr,
                )
                saved_files.extend(main_files)

            # 保存文本备份（仅当没任何文本格式输出时）
            if save_text_backup:
                has_text = any(k in ('output_txt', 'output_md') for k, _ in saved_files)
                if not has_text:
                    txt_path = output_path.parent / f"{output_path.stem}.txt"
                    self.processor._write_plain_text(anonymized_content, str(txt_path))
                    saved_files.append(("text_backup", str(txt_path)))

            # 保存映射表
            if save_mapping:
                mapping_path = output_path.parent / f"{output_path.stem}_mapping.json"
                self.processor.write_mapping(detailed_mapping, str(mapping_path))
                saved_files.append(("mapping_file", str(mapping_path)))

            # 更新结果信息
            for key, path in saved_files:
                result_info[key] = path

        return {
            "action": "anonymize_file",
            "status": "success",
            "result": result_info
        }

    def analyze_file(
        self,
        input_path: str,
        only_types: List[str] = None,
        exclude_types: List[str] = None,
        use_ocr: bool = False,
        ocr_engine: str = 'rapidocr',
        with_context: bool = False,
        context_window: int = 40
    ) -> Dict:
        """
        分析文件（不实际脱敏）

        Args:
            input_path: 输入文件路径
            only_types: 只分析指定类型
            exclude_types: 排除指定类型
            use_ocr: 是否使用OCR
            ocr_engine: OCR 引擎 'rapidocr'（默认）| 'paddleocr' | 'tesseract'
            with_context: 是否附带前后文
            context_window: 上下文窗口大小（字符数）

        Returns:
            分析结果
        """
        input_path = Path(input_path)

        if not input_path.exists():
            return {"error": f"文件不存在: {input_path}"}

        try:
            content = self.processor.extract_text(str(input_path), use_ocr=use_ocr, ocr_engine=ocr_engine)
        except Exception as e:
            return {"error": f"读取文件失败: {e}"}

        analysis = self.analyze_text(content, only_types, exclude_types,
                                     with_context=with_context, context_window=context_window)

        return {
            "action": "analyze_file",
            "status": "success",
            "result": {
                "input_file": str(input_path),
                "analysis": analysis
            }
        }

    def get_supported_types(self) -> Dict[str, str]:
        """获取所有支持的类型及其描述"""
        return self.pattern_detector.get_all_types()

    def reset(self):
        """重置状态"""
        self.masker.reset()
        self.entity_detector.clear()
