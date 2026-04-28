"""
Text Masker - Smart data masking with various strategies
文本掩码器 - 支持多种脱敏策略的智能数据掩码
"""

from typing import Dict, List, Tuple
from collections import defaultdict


class TextMasker:
    """文本掩码器"""

    # 占位符风格切换：english_bracket（默认 [PERSON_1]）/ chinese_angle（<人物1>）/ chinese_bracket（〔姓名1〕）
    # 切换时 placeholder_templates 整体替换；不影响 partial 掩码
    _CHINESE_LABELS = {
        'person': '人物', 'company': '公司', 'address': '地址', 'full_address': '地址',
        'law_firm': '律所', 'institution': '机构', 'government': '政府', 'court': '法院',
        'city': '城市', 'district': '区县', 'location': '地点', 'signature': '签名',
        'bank_name': '银行', 'branch_name': '支行', 'account_name': '账户名',
        'project_name': '项目', 'product_name': '产品', 'asset': '资产',
        'vehicle': '车辆', 'property': '房产', 'stock': '股票', 'seal': '印章',
        'id_card': '身份证', 'phone': '电话', 'fax': '传真', 'toll_free': '电话',
        'email': '邮箱', 'bank_account': '银行卡', 'passport': '护照',
        'hk_macau_pass': '港澳通行证', 'taiwan_pass': '台胞证', 'military_id': '军官证',
        'credit_code': '社会信用代码', 'case_number': '案号',
        'contract_number': '合同号', 'invoice_number': '发票号',
        'license_plate': '车牌', 'vin': '车架号', 'ip_address': 'IP地址',
        'mac_address': 'MAC地址', 'amount': '金额', 'price': '价格',
        'date': '日期', 'time': '时间', 'datetime': '时间', 'postal_code': '邮编',
        'house_number': '房号', 'website': '网址', 'org_code': '机构代码',
        'tax_number': '税号', 'social_account': '社交账号', 'other': '其他',
        'property_cert': '产权证', 'permit_number': '证书号', 'patent_number': '专利号',
        'document_number': '文书号', 'secret': '密钥', 'unknown': '未知',
    }

    def __init__(self):
        self.mapping = {}  # 原始值 -> 占位符
        self.reverse_mapping = {}  # 占位符 -> 原始值
        self.counter = defaultdict(int)
        self.replacement_log = []
        self.abbreviation_map = {}  # 简称 -> 全称
        self.placeholder_style = 'english_bracket'  # 默认风格
        # 默认英文模板的副本，切回 english_bracket 时复原用
        self._default_templates = None  # 在 placeholder_templates 定义后填充

        # 掩码策略定义
        # 可以是 "placeholder"（占位符）或 "partial"（部分掩码）
        self.mask_strategies = {
            # ========== 默认策略: 占位符 ==========
            'person': 'placeholder',
            'company': 'placeholder',
            'address': 'placeholder',
            'law_firm': 'placeholder',
            'institution': 'placeholder',
            'government': 'placeholder',
            'city': 'placeholder',
            'district': 'placeholder',
            'location': 'placeholder',
            'signature': 'placeholder',
            'bank_name': 'placeholder',
            'branch_name': 'placeholder',
            'account_name': 'placeholder',
            'project_name': 'placeholder',
            'product_name': 'placeholder',
            'asset': 'placeholder',
            'vehicle': 'placeholder',
            'property': 'placeholder',
            'stock': 'placeholder',
            'seal': 'placeholder',
            'case_number': 'placeholder',
            'contract_number': 'placeholder',
            'invoice_number': 'placeholder',

            # ========== 部分掩码策略 ==========
            'id_card': 'partial',
            'phone': 'partial',
            'fax': 'partial',
            'toll_free': 'partial',
            'bank_account': 'partial',
            'email': 'partial',
            'passport': 'partial',
            'hk_macau_pass': 'partial',
            'taiwan_pass': 'partial',
            'military_id': 'partial',
            'credit_code': 'partial',
            'license_plate': 'partial',
            'vin': 'partial',

            # ========== 占位符（简单类型） ==========
            'ip_address': 'placeholder',
            'mac_address': 'placeholder',
            'amount': 'placeholder',
            'price': 'placeholder',
            'date': 'placeholder',
            'time': 'placeholder',
            'datetime': 'placeholder',
            'postal_code': 'placeholder',
            'house_number': 'placeholder',
            'website': 'placeholder',
            'org_code': 'placeholder',
            'tax_number': 'placeholder',
            'social_account': 'placeholder',
            'other': 'placeholder',
            'full_address': 'placeholder',
            'property_cert': 'placeholder',
            'permit_number': 'placeholder',
            'patent_number': 'placeholder',
            'document_number': 'placeholder',
            'project_name': 'placeholder',
            'secret': 'placeholder',  # API key / token（LLM 检测专有）
        }

        # 占位符模板
        self.placeholder_templates = {
            'person': '[PERSON_{}]',
            'company': '[COMPANY_{}]',
            'address': '[ADDRESS_{}]',
            'law_firm': '[LAW_FIRM_{}]',
            'institution': '[INSTITUTION_{}]',
            'government': '[GOVERNMENT_{}]',
            'court': '[COURT_{}]',
            'city': '[CITY_{}]',
            'district': '[DISTRICT_{}]',
            'location': '[LOCATION_{}]',
            'signature': '[SIGNATURE_{}]',
            'bank_name': '[BANK_NAME_{}]',
            'branch_name': '[BRANCH_NAME_{}]',
            'account_name': '[ACCOUNT_NAME_{}]',
            'project_name': '[PROJECT_NAME_{}]',
            'product_name': '[PRODUCT_NAME_{}]',
            'asset': '[ASSET_{}]',
            'vehicle': '[VEHICLE_{}]',
            'property': '[PROPERTY_{}]',
            'stock': '[STOCK_{}]',
            'seal': '[SEAL_{}]',
            'id_card': '[ID_CARD_{}]',
            'phone': '[PHONE_{}]',
            'fax': '[FAX_{}]',
            'toll_free': '[PHONE_{}]',
            'email': '[EMAIL_{}]',
            'bank_account': '[BANK_ACCOUNT_{}]',
            'passport': '[PASSPORT_{}]',
            'hk_macau_pass': '[HK_MACAU_PASS_{}]',
            'taiwan_pass': '[TAIWAN_PASS_{}]',
            'military_id': '[MILITARY_ID_{}]',
            'credit_code': '[CREDIT_CODE_{}]',
            'case_number': '[CASE_NUMBER_{}]',
            'contract_number': '[CONTRACT_NUMBER_{}]',
            'invoice_number': '[INVOICE_NUMBER_{}]',
            'license_plate': '[LICENSE_PLATE_{}]',
            'vin': '[VIN_{}]',
            'ip_address': '[IP_ADDRESS_{}]',
            'mac_address': '[MAC_ADDRESS_{}]',
            'amount': '[AMOUNT_{}]',
            'price': '[PRICE_{}]',
            'date': '[DATE_{}]',
            'time': '[TIME_{}]',
            'datetime': '[DATETIME_{}]',
            'postal_code': '[POSTAL_CODE_{}]',
            'house_number': '[HOUSE_NUMBER_{}]',
            'website': '[WEBSITE_{}]',
            'org_code': '[ORG_CODE_{}]',
            'tax_number': '[TAX_NUMBER_{}]',
            'social_account': '[SOCIAL_ACCOUNT_{}]',
            'other': '[OTHER_{}]',
            'full_address': '[ADDRESS_{}]',
            'property_cert': '[PROPERTY_CERT_{}]',
            'permit_number': '[PERMIT_{}]',
            'patent_number': '[PATENT_{}]',
            'document_number': '[DOC_NUMBER_{}]',
            'project_name': '[PROJECT_{}]',
            'secret': '[SECRET_{}]',
            'unknown': '[UNKNOWN_{}]',
        }
        # 保留默认英文模板的副本，切风格时用作复原参考
        self._default_templates = dict(self.placeholder_templates)

    def set_strategy(self, entity_type: str, strategy: str):
        """
        设置指定类型的掩码策略

        Args:
            entity_type: 实体类型
            strategy: 'placeholder'（占位符）或 'partial'（部分掩码）
        """
        if strategy in ['placeholder', 'partial']:
            self.mask_strategies[entity_type] = strategy

    def set_placeholder_style(self, style: str):
        """
        设置占位符风格：
          - english_bracket: [PERSON_1] [COMPANY_1]（默认）
          - chinese_angle:   <人物1> <公司1>
          - chinese_bracket: 〔姓名1〕〔公司1〕
        切换后所有 placeholder 类型的模板会被一次性替换。
        partial 掩码（如 138****5678）不受影响。
        """
        if style not in ('english_bracket', 'chinese_angle', 'chinese_bracket'):
            return
        self.placeholder_style = style
        if style == 'english_bracket':
            # 复原默认英文模板
            for etype, tpl in self._default_templates.items():
                self.placeholder_templates[etype] = tpl
            return
        # 中文风格：基于 _CHINESE_LABELS 重建模板
        wrappers = {
            'chinese_angle': ('<', '>'),
            'chinese_bracket': ('〔', '〕'),
        }
        left, right = wrappers[style]
        for etype in self.placeholder_templates:
            label = self._CHINESE_LABELS.get(etype, '其他')
            self.placeholder_templates[etype] = f'{left}{label}{{}}{right}'

    def set_all_strategy(self, strategy: str):
        """
        设置所有类型的掩码策略

        Args:
            strategy: 'placeholder' 或 'partial'
        """
        for entity_type in self.mask_strategies:
            self.mask_strategies[entity_type] = strategy

    def _mask_partial(self, text: str, entity_type: str) -> str:
        """
        部分掩码 - 保留部分原始信息

        Args:
            text: 原始文本
            entity_type: 实体类型

        Returns:
            部分掩码后的文本
        """
        if entity_type == 'id_card':
            # 身份证：保留前3位和后2位
            if len(text) >= 5:
                return text[:3] + '*' * (len(text) - 5) + text[-2:]
            return '*' * len(text)

        elif entity_type in ['phone', 'fax', 'toll_free']:
            # 手机号/电话：保留前3位和后2位
            digits = ''.join([c for c in text if c.isdigit()])
            if len(digits) >= 5:
                masked = digits[:3] + '*' * (len(digits) - 5) + digits[-2:]
                # 尝试恢复原始格式
                result = []
                digit_idx = 0
                for c in text:
                    if c.isdigit() and digit_idx < len(masked):
                        result.append(masked[digit_idx])
                        digit_idx += 1
                    else:
                        result.append(c)
                return ''.join(result)
            return text

        elif entity_type == 'bank_account':
            # 银行卡号：保留前4位和后4位
            if len(text) >= 8:
                return text[:4] + '*' * (len(text) - 8) + text[-4:]
            return '*' * len(text)

        elif entity_type == 'email':
            # 邮箱：保留域名，用户名部分掩码
            if '@' in text:
                username, domain = text.split('@', 1)
                if len(username) <= 2:
                    masked_username = '*' * len(username)
                else:
                    masked_username = username[:2] + '*' * (len(username) - 2)
                return f'{masked_username}@{domain}'
            return text

        elif entity_type in ['passport', 'hk_macau_pass', 'taiwan_pass', 'military_id']:
            # 护照等：保留前2位和后2位
            if len(text) >= 4:
                return text[:2] + '*' * (len(text) - 4) + text[-2:]
            return '*' * len(text)

        elif entity_type == 'credit_code':
            # 统一社会信用代码：保留前4位和后4位
            if len(text) >= 8:
                return text[:4] + '*' * (len(text) - 8) + text[-4:]
            return '*' * len(text)

        elif entity_type == 'license_plate':
            # 车牌号：保留前2位和后1位
            if len(text) >= 3:
                return text[:2] + '*' * (len(text) - 3) + text[-1:]
            return '*' * len(text)

        elif entity_type == 'vin':
            # VIN：保留前3位和后3位
            if len(text) >= 6:
                return text[:3] + '*' * (len(text) - 6) + text[-3:]
            return '*' * len(text)

        elif entity_type == 'person':
            # 中文人名：保留姓氏，名字星号化（张三 → 张*；张三丰 → 张**）
            if len(text) >= 2:
                return text[0] + '*' * (len(text) - 1)
            return text

        elif entity_type in ('company', 'law_firm', 'institution', 'court',
                              'government', 'bank_name'):
            # 公司/机构：保留品牌首字 + 完整后缀，使读者能辨识"是个公司"但不知具体哪家
            # 例：北京XX（深圳）律师事务所 → 北*****律师事务所
            #     深圳市XX物流有限公司 → 深*****有限公司
            #     广东省深圳市龙岗区人民法院 → 广*****人民法院
            suffixes = [
                '中级人民法院', '高级人民法院', '人民法院', '人民检察院',
                '律师事务所', '会计师事务所', '事务所',
                '股份有限公司', '有限责任公司', '集团有限公司', '有限公司',
                '集团公司', '管理委员会', '人民政府',
                '公司', '集团', '股份', '银行', '司法厅', '司法部',
            ]
            for sfx in sorted(suffixes, key=len, reverse=True):
                if text.endswith(sfx):
                    core = text[:-len(sfx)]
                    if len(core) >= 1:
                        return core[0] + '*' * max(len(core) - 1, 1) + sfx
                    return sfx
            # 没有匹配后缀：保留首字 + 星号
            if len(text) >= 2:
                return text[0] + '*' * (len(text) - 1)
            return '*' * len(text)

        # 默认：全部替换为星号
        return '*' * len(text)

    def set_abbreviation_map(self, abbrev_map: dict):
        """设置简称→全称映射，使简称与全称共享同一占位符"""
        self.abbreviation_map = abbrev_map or {}

    def _mask_placeholder(self, text: str, entity_type: str) -> str:
        """
        占位符掩码 - 使用 [TYPE_1] 格式

        Args:
            text: 原始文本
            entity_type: 实体类型

        Returns:
            占位符文本
        """
        key = (entity_type, text)
        if key not in self.mapping:
            # 检查是否为简称，若是则复用全称的占位符
            if text in self.abbreviation_map:
                full_name = self.abbreviation_map[text]
                full_key = (entity_type, full_name)
                if full_key in self.mapping:
                    self.mapping[key] = self.mapping[full_key]
                    return self.mapping[key]
            self.counter[entity_type] += 1
            template = self.placeholder_templates.get(entity_type, self.placeholder_templates['unknown'])
            placeholder = template.format(self.counter[entity_type])
            self.mapping[key] = placeholder
            self.reverse_mapping[placeholder] = (entity_type, text)
        return self.mapping[key]

    def mask(self, text: str, entity_type: str) -> str:
        """
        掩码单个实体

        Args:
            text: 原始文本
            entity_type: 实体类型

        Returns:
            掩码后的文本
        """
        strategy = self.mask_strategies.get(entity_type, 'placeholder')

        if strategy == 'partial':
            masked = self._mask_partial(text, entity_type)
            # 记录映射关系，确保可逆
            key = (entity_type, text)
            if key not in self.mapping:
                self.mapping[key] = masked
                self.reverse_mapping[masked] = (entity_type, text)
            return masked
        else:
            return self._mask_placeholder(text, entity_type)

    def mask_all(self, text: str, entities: List[Tuple[str, str, int]]) -> Tuple[str, Dict]:
        """
        批量掩码文本中的所有实体

        Args:
            text: 原始文本
            entities: 实体列表 [(实体文本, 实体类型, 位置), ...]

        Returns:
            (掩码后文本, 详细映射信息)
        """
        self.mapping = {}
        self.reverse_mapping = {}
        self.counter = defaultdict(int)
        self.replacement_log = []

        result = text

        # 按位置从后往前处理，避免位置偏移问题
        # 或者按长度降序排序，避免子字符串匹配问题
        sorted_entities = sorted(entities, key=lambda x: (-len(x[0]), x[2]))

        # 先收集所有替换，然后一次性应用
        replacements = []
        for entity_text, entity_type, pos in sorted_entities:
            # 检查是否已经被覆盖
            skip = False
            for repl in replacements:
                existing_pos = repl[2]
                existing_len = repl[3]
                if existing_pos <= pos < existing_pos + existing_len:
                    skip = True
                    break
                if pos <= existing_pos < pos + len(entity_text):
                    skip = True
                    break
            if skip:
                continue

            masked_text = self.mask(entity_text, entity_type)
            replacements.append((entity_text, masked_text, pos, len(entity_text), entity_type))

        # 按位置从后往前应用替换
        replacements.sort(key=lambda x: -x[2])

        for entity_text, masked_text, pos, length, entity_type in replacements:
            context_before = result[max(0, pos - 40):pos]
            context_after = result[pos + length:pos + length + 40]

            self.replacement_log.append({
                "original_text": entity_text,
                "masked_text": masked_text,
                "type": entity_type,
                "position": pos,
                "context_before": context_before,
                "context_after": context_after
            })

            result = result[:pos] + masked_text + result[pos + length:]

        # 构建映射表
        mapping_result = {}
        for (etype, original), placeholder in self.mapping.items():
            if placeholder not in mapping_result:
                mapping_result[placeholder] = {
                    'type': etype,
                    'original': original
                }

        detailed_mapping = {
            "metadata": {
                "entity_count": len(mapping_result),
                "replacements_made": len(self.replacement_log)
            },
            "mapping": mapping_result,
            "replacement_log": self.replacement_log
        }

        return result, detailed_mapping

    def get_mapping(self) -> Dict:
        """获取简化版映射表"""
        result = {}
        for (etype, original), placeholder in self.mapping.items():
            result[placeholder] = {'type': etype, 'original': original}
        return result

    def reset(self):
        """重置状态"""
        self.mapping = {}
        self.reverse_mapping = {}
        self.counter = defaultdict(int)
        self.replacement_log = []
        self.abbreviation_map = {}
