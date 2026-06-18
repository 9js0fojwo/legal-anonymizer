"""
Pattern-based Sensitive Data Detector
基于正则表达式的敏感数据检测器
"""

import re
from typing import Dict, List, Tuple


class PatternDetector:
    """正则表达式模式检测器"""

    # 优先级定义（数字越小优先级越高）
    # 高优先级的匹配会覆盖低优先级的重叠匹配
    PATTERN_PRIORITY = {
        'datetime': 1,       # 最具体的日期时间格式
        'id_card': 2,        # 身份证（18位有校验，最具体）
        'passport': 2,
        'military_id': 2,
        'hk_macau_pass': 2,
        'taiwan_pass': 2,
        'credit_code': 2,    # 统一社会信用代码（18位有校验）
        'case_number': 3,
        'contract_number': 3,
        'invoice_number': 3,
        'phone': 3,
        'toll_free': 3,
        'fax': 3,
        'email': 3,
        'website': 3,
        'mac_address': 3,
        'ip_address': 3,
        'license_plate': 3,
        'vin': 3,
        'amount': 3,
        'price': 3,
        'org_code': 3,
        'date': 4,
        'time': 4,
        'bank_account': 5,   # 16-19位纯数字，容易误匹配
        'tax_number': 6,     # 15-20位纯数字，最宽泛
        'social_account': 2,  # 社交账号（QQ/微信）
        'full_address': 2,    # 完整地址优先级高，避免被子模式拆分
        'property_cert': 2,  # 不动产权证比 case_number 更具体，优先抢占
        'permit_number': 3,
        'house_number': 7,
        'postal_code': 8,    # 6位纯数字，最容易误匹配
        'patent_number': 3,
        'trademark_number': 3,
        'lawyer_license': 3,
        'long_alphanumeric': 6,
        'document_number': 3,
        'project_name': 5,   # 项目名称容易误匹配，优先级略低
    }

    def __init__(self):
        # 所有支持的正则表达式模式
        # 顺序很重要：先匹配更具体的模式，避免部分匹配
        self.patterns = {
            # ========== 身份证件类 ==========
            # 身份证号 (18位，带校验)
            'id_card': r'(?<!\d)[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)',

            # 护照号（含 PRC 标准 E/G+8 / 港澳台 P+7 / H+8 / M+7 / 新版双字母前缀如 EM / EH / EJ + 7 位数字）
            'passport': r'(?<![A-Za-z0-9])(?:[EeGg]\d{8}|[Pp]\d{7}|[Hh]\d{8}|[Mm]\d{7}|E[A-Z]\d{7})(?![A-Za-z0-9])',

            # 港澳通行证
            'hk_macau_pass': r'(?<![A-Za-z0-9])[WwCc]\d{8}(?![A-Za-z0-9])',

            # 台湾通行证
            'taiwan_pass': r'(?<![A-Za-z0-9])[Tt]\d{8}(?![A-Za-z0-9])',

            # 军官证
            'military_id': r'(?<![A-Za-z0-9])[军士官兵]\s?字\s?第\s?\d{4,8}\s?号(?![A-Za-z0-9])',

            # ========== 企业/机构类 ==========
            # 统一社会信用代码 (18位)
            'credit_code': r'(?<![0-9A-HJ-NPQRTUWXY])[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}(?![0-9A-HJ-NPQRTUWXY])',

            # 组织机构代码
            'org_code': r'(?<![0-9A-HJ-NPQRTUWXY])[0-9A-HJ-NPQRTUWXY]{8}-[0-9A-HJ-NPQRTUWXY](?![0-9A-HJ-NPQRTUWXY])',

            # 税务登记号
            'tax_number': r'(?<!\d)\d{15,20}(?!\d)',

            # ========== 案件/合同类 ==========
            # 案号（严格匹配：年份 + 法院代码 + 案件类型 + 编号 + 号）
            # 支持OCR变体括号：()（）〈〉《》﹝﹞〔〕
            'case_number': r'[\(（〈《﹝〔]\s*\d{4}\s*[\)）〉》﹞〕]\s*[\u4e00-\u9fa5A-Za-z0-9#\s]{1,25}号',

            # 合同编号
            'contract_number': r'(?:合同编号|协议编号|Contract[-\s]?No)[：:.]\s*[A-Za-z0-9\-_]{6,30}',

            # 发票号码
            'invoice_number': r'(?:发票号码|发票代码)[：:.]\s*\d{8,20}',

            # ========== 联系方式类 ==========
            # 手机号 (11位，1开头)
            'phone': r'(?<!\d)1[3-9]\d{9}(?![0-9A-Za-z])',

            # 座机/传真
            'fax': r'(?<!\d)(?:0\d{2,3}[- ]?\d{7,8}|\(0\d{2,3}\)\d{7,8})(?!\d)',

            # 400/800免费电话
            'toll_free': r'(?<!\d)[48]00[- ]?\d{3}[- ]?\d{4}(?!\d)',

            # 邮箱
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',

            # 网址/URL
            'website': r'https?://[^\s<>"{}|\\^`\[\]））、。，；]+|(?<![A-Za-z0-9.])www\.[A-Za-z0-9][-A-Za-z0-9.]*\.[A-Za-z]{2,}(?:/[^\s<>"{}|\\^`\[\]））、。，；]*)?',

            # ========== 社交账号类 ==========
            # QQ 号 / 微信号 / 微博号 / VX 缩写
            # 微信：'微信号: abc-123' 'wechat: john_doe' 'VX：xxxxxx'，需字母开头
            # QQ：'QQ：12345' 'Q号: 12345' 不在单词中（避免 'QQA' 误匹配）
            # 微博：'微博: xxx' 'weibo: xxx'
            'social_account': (
                r'(?i)(?:微信号?|wechat|VX|微博号?|weibo)[\s:：]*[a-zA-Z][a-zA-Z0-9_\-]{4,19}'
                r'|(?<!\w)(?i:QQ号码?|QQ号|Q号|QQ)[\s:：]*[1-9]\d{4,9}(?!\d)'
            ),

            # ========== 网络标识类 ==========
            # IP地址
            'ip_address': r'(?<!\d)(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?!\d)',

            # MAC地址
            'mac_address': r'(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}',

            # ========== 金融类 ==========
            # 银行卡号 (16-19位 标准卡号 + "账号:数字" 上下文敏感（含 8-15 位短账号）)
            'bank_account': (
                r'(?<!\d)\d{16,19}(?!\d)'
                r'|(?:账号|账户|帐号|帐户|户口号码|户口號碼|银行账号|银行账户|收款账号)[：:.\s]*\d{8,19}'
            ),

            # 金额（人民币）- 含阿拉伯数字和中文大写
            'amount': (
                # ¥ / 人民币 / ￥ 前缀 + 任意位数（含 ¥20800000.00 元 这种无千分位）
                # 后缀 元 可选：'¥1234.56' 也能匹配
                r'(?:¥|人民币|￥)\s*\d{1,3}(?:[,，]\d{3})+(?:\.\d{1,2})?\s*(?:元|万元|亿元)?'
                r'|(?:¥|人民币|￥)\s*\d+(?:\.\d{1,2})?\s*(?:元|万元|亿元)?'
                # 带千分位分组：1,234,567.89 元
                r'|(?<![,，\d.])\d{1,3}(?:[,，]\d{3})+(?:\.\d{1,2})?\s*(?:元|万元|亿元)'
                # 无千分位的整数/小数：3799.2 元；加点在 lookbehind 防止捕获小数尾部
                r'|(?<![,，\d.])\d+(?:\.\d{1,2})?\s*(?:元|万元|亿元)'
                # 中文大写：补"零"字（"贰仟零捌拾万元整" 才不会被切断）
                r'|[零壹贰叁肆伍陆柒捌玖拾佰仟万亿]+[元圆][整正]?(?:[零壹贰叁肆伍陆柒捌玖拾]+[角分])*'
            ),

            # 其他货币金额（含更多币种）
            'price': r'(?:USD|EUR|GBP|HKD|JPY|CNY|RMB|AUD|CAD|CHF|US\$|€|£|HK\$)\s*[\d,]+\.?\d*',

            # ========== 车辆类 ==========
            # 车牌号
            'license_plate': r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{4,5}[A-Z0-9挂学警港澳]?',

            # 车辆识别代号(VIN)
            'vin': r'(?<![A-HJ-NPR-Z0-9])[A-HJ-NPR-Z0-9]{17}(?![A-HJ-NPR-Z0-9])',

            # ========== 日期时间类 ==========
            # 日期（多种格式）
            'date': r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?|\d{4}年\d{1,2}月\d{1,2}日',

            # 时间
            'time': r'\d{1,2}:\d{2}(?::\d{2})?|\d{1,2}时\d{1,2}分\d{1,2}秒?',

            # 日期时间
            'datetime': r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号\s]\s*\d{1,2}:\d{2}(?::\d{2})?',

            # ========== 地址类 ==========
            # 完整地址（省/市/区/县/镇/街道 + 建筑物/道路/场所描述）
            'full_address': r'[\u4e00-\u9fa5]{2,10}(?:省|市|区|县|镇|街道)[\u4e00-\u9fa5\d]{2,50}(?:层|楼|室|栋|幢|单元|\d号|苑|园|城|座|铺|店|馆|厅|堂|坊|府|邸|庄|寓|舍|宅|村|组|路|街|巷|弄|里|胡同|大道|公路|大街|小区|花园|工业区|产业园|商务中心|\d{2,5})(?![\u4e00-\u9fa5\d%％股权])',

            # 邮政编码
            'postal_code': r'(?<!\d)\d{6}(?!\d)',

            # 门牌号（单元/弄/栋/座/楼/室，注意单元是两字不能拆进字符类）
            'house_number': r'\d+(?:弄|单元|号楼|号院|号室|栋|座|楼|室)(?:-\d+)?',

            # ========== 证件/证书编号类 ==========
            # 房地产证号 / 不动产权证书号
            # 旧式：深房地字第 XXXXX 号、FH XXXXX 号
            # 新式：粤(2024)深圳市不动产权第 0123456 号
            'property_cert': (
                r'(?:[\u4e00-\u9fa5]{1,4}房地字第|FH)\s*\d{5,15}\s*号?'
                # 不动产权第 N 号：可前缀省/直辖市/区县/(年份) 等组合
                r'|(?:[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼])?'
                r'\s*(?:[\(（]\s*\d{4}\s*[\)）])?\s*[\u4e00-\u9fa5]{2,12}'
                r'\s*不动产权第\s*[A-Za-z0-9\s]{1,15}\s*号'
            ),

            # 通用证书/批文编号（XX字 NNN 号、XX字第 NNN 号）
            'permit_number': r'[\u4e00-\u9fa5]{2,8}字\s*(?:第\s*)?\d{2,15}\s*号',

            # ========== 专利/商标/著作权编号类 ==========
            # 专利/商标/著作权申请号（含国际专利局代码）
            'patent_number': r'(?:专利|商标|著作权)(?:申请|注册|登记)号[：:]\s*[A-Z0-9.]+|(?:CN|US|EP|JP|WO|KR|GB|DE|FR|CA|AU)\d{4,}[A-Z]?\d?',

            # 商标注册号（第 + 数字 + 号）
            'trademark_number': r'(?:商标注册号|商标号|商标编号|第)\s*\d{4,12}\s*号',

            # 律师执业证号（16-18位）
            'lawyer_license': r'(?:律师执业证|律师资格证|律师证|执业证|执业证书)\s*(?:号|号码|编号)?[：:\s]*\d{15,18}',

            # 连续字母/数字/符号（25-100位，如 token、API key、哈希值）
            'long_alphanumeric': r'[A-Za-z0-9+/=._\-:]{25,100}',

            # 合同/文件编号（扩展：协议号、函件编号等）
            'document_number': r'(?:文件编号|文件号|函件编号|协议号|编号)[：:.]\s*[A-Za-z0-9\-_]{4,30}',

            # ========== 项目名称类 ==========
            # 项目/工程/系统/平台名称
            'project_name': r'([\u4e00-\u9fa5]{2,10}(?:项目|工程|系统|平台|计划))(?![\u4e00-\u9fa5])',
        }

        # 模式类型的中文描述
        self.type_names = {
            'id_card': '身份证号',
            'passport': '护照号',
            'hk_macau_pass': '港澳通行证',
            'taiwan_pass': '台湾通行证',
            'military_id': '军官证',
            'credit_code': '统一社会信用代码',
            'org_code': '组织机构代码',
            'tax_number': '税务登记号',
            'case_number': '案号',
            'contract_number': '合同编号',
            'invoice_number': '发票号码',
            'phone': '手机号',
            'fax': '座机/传真',
            'toll_free': '400/800电话',
            'email': '邮箱',
            'website': '网址',
            'ip_address': 'IP地址',
            'mac_address': 'MAC地址',
            'bank_account': '银行卡号',
            'amount': '金额',
            'price': '价格',
            'license_plate': '车牌号',
            'vin': '车辆识别码',
            'date': '日期',
            'time': '时间',
            'datetime': '日期时间',
            'postal_code': '邮政编码',
            'house_number': '门牌号',
            'social_account': 'QQ/微信号',
            'full_address': '完整地址',
            'property_cert': '房地产证号',
            'permit_number': '证书/批文编号',
            'patent_number': '专利/商标编号',
            'trademark_number': '商标注册号',
            'lawyer_license': '律师执业证号',
            'long_alphanumeric': '连续字母/数字/符号',
            'document_number': '文件编号',
            'project_name': '项目名称',
        }

    def detect(self, text: str, only_types: List[str] = None, exclude_types: List[str] = None) -> List[Tuple[str, str, int]]:
        """
        检测文本中的敏感数据

        Args:
            text: 输入文本
            only_types: 只检测指定类型
            exclude_types: 排除指定类型

        Returns:
            列表 [(匹配文本, 类型, 起始位置), ...]
        """
        raw_results = []

        for pattern_name, pattern in self.patterns.items():
            if only_types and pattern_name not in only_types:
                continue
            if exclude_types and pattern_name in exclude_types:
                continue

            for match in re.finditer(pattern, text):
                match_text = match.group(0)
                start_pos = match.start()
                priority = self.PATTERN_PRIORITY.get(pattern_name, 99)
                raw_results.append((match_text, pattern_name, start_pos, priority))

        # 按优先级排序（优先级高的先处理），同优先级按匹配长度降序
        raw_results.sort(key=lambda x: (x[3], -len(x[0])))

        # 消除重叠：高优先级的匹配覆盖低优先级的
        filtered = []
        occupied = []  # [(start, end), ...]

        for match_text, pattern_name, start_pos, priority in raw_results:
            end_pos = start_pos + len(match_text)

            # 检查是否与已确认的高优先级匹配重叠
            overlap = False
            for occ_start, occ_end in occupied:
                if start_pos < occ_end and end_pos > occ_start:
                    overlap = True
                    break

            if not overlap:
                # 地址类后处理：去掉"住所""地址"等非地址前缀
                if pattern_name == 'full_address':
                    for prefix_word in ('住所地', '住所', '地址'):
                        if match_text.startswith(prefix_word):
                            match_text = match_text[len(prefix_word):]
                            start_pos += len(prefix_word)
                            break
                    # 排除法院/检察院名称（不是地址）
                    if match_text.endswith(('人民法院', '人民检察院', '中级人民法院', '高级人民法院')):
                        continue
                    # 排除法律文件/法规引用（不是地址）
                    legal_doc_terms = ('证券交易所', '交易所', '监管指引', '管理办法', '管理条例', '实施细则')
                    if any(term in match_text for term in legal_doc_terms):
                        continue
                    # 排除含"上市"（动词：上市发行）的误匹配，不是地名中的"市"
                    if '上市' in match_text:
                        continue
                # 邮政编码后处理：排除证券代码/债券代码等
                if pattern_name == 'postal_code':
                    context_before = text[max(0, start_pos - 30):start_pos]
                    # 去除换行后检查，处理"股票代\n码"等跨行情况
                    context_before_noline = context_before.replace('\n', '').replace('\r', '')
                    securities_keywords = (
                        '证券代码', '债券代码', '股票代码', '基金代码',
                        '代码：', '代码:', '代码为', '代码\u201c', '代码"',
                        '代码 ', '码为', '证券简称', '股票简称',
                    )
                    if any(kw in context_before_noline for kw in securities_keywords):
                        continue
                    # 排除金额数字被误匹配为邮编（后面跟万元/元/亿元）
                    context_after = text[end_pos:min(len(text), end_pos + 5)]
                    if any(kw in context_after for kw in ('万元', '元', '亿元')):
                        continue
                    # 排除算术表达式中的数字（后跟乘号、加减号、月/天/年/日）
                    ctx_after_strip = context_after.strip()
                    if ctx_after_strip and ctx_after_strip[0] in 'x×*+-' :
                        continue
                    if any(ctx_after_strip.startswith(kw) for kw in ('月', '天', '年', '日', 'x', '×')):
                        continue
                    # 排除前面是加减乘除或等号的数字（算式中间）
                    ctx_before_1 = text[max(0, start_pos - 3):start_pos].strip()
                    if ctx_before_1 and ctx_before_1[-1] in '+-x×*=(（':
                        continue
                    # 排除常见股票代码前缀（沪深交易所特定号段）
                    # 仅当附近无邮编关键词时才排除
                    stock_prefixes = ('600', '601', '603', '605', '688', '689',
                                      '000', '001', '002', '003', '300', '301')
                    if match_text.startswith(stock_prefixes):
                        postal_ctx = text[max(0, start_pos - 20):min(len(text), end_pos + 10)]
                        postal_ctx_clean = postal_ctx.replace('\n', '').replace('\r', '')
                        postal_kws = ('邮编', '邮政编码', '邮政', '邮区')
                        if not any(kw in postal_ctx_clean for kw in postal_kws):
                            continue
                # 金额后处理：数字边界检查，防止部分数字被截断匹配
                if pattern_name in ('amount', 'price'):
                    # 检查匹配前方是否紧邻数字（部分数字被截断）
                    if start_pos > 0 and text[start_pos - 1].isdigit():
                        continue
                    # 检查匹配后方是否紧邻数字或连字符
                    # 注意：当匹配以"元/圆/万元/亿元"等显式后缀结尾时，已有清晰的金额边界，
                    # 后面紧跟数字属于下一个金额（OCR 表格里相邻金额会粘连），不应跳过。
                    if end_pos < len(text):
                        next_char = text[end_pos]
                        ends_with_yuan_suffix = match_text.endswith(
                            ('元', '圆', '万元', '亿元', '元整', '圆整')
                        )
                        if (next_char.isdigit() or next_char == '-') and not ends_with_yuan_suffix:
                            continue
                    # 排除"第X条/款/项/章/节"等法规条文引用（例如"第2条"被误判为"2元"）
                    ctx_before = text[max(0, start_pos - 10):start_pos]
                    if any(kw in ctx_before for kw in ('第', '本条', '上条', '前条', '下条')):
                        # 前面 4 字内含"第"且后面紧接"元"字
                        nearby = text[max(0, start_pos - 4):end_pos + 2]
                        if '第' in nearby and '元' in match_text:
                            continue
                # 项目名称后处理：排除过于泛指的项目名
                if pattern_name == 'project_name':
                    # 使用捕获组的文本（去掉lookbehind/lookahead）
                    captured = match.group(1) if match.lastindex and match.lastindex >= 1 else match_text
                    generic_projects = {
                        '测试项目', '示例项目', '工程项目', '系统项目', '本项目', '该项目',
                        '其他项目', '相关项目', '涉案项目', '目标项目', '拟建项目',
                        '建设项目', '投资项目', '合作项目', '试点项目', '重点项目',
                        '改造工程', '建设工程', '施工工程', '本工程', '该工程',
                        '管理系统', '信息系统', '业务系统', '本系统', '该系统', '操作系统',
                        '交易平台', '服务平台', '管理平台', '本平台', '该平台',
                        '网络投票平台', '投票平台', '交易系统', '信息披露平台',
                        '行动计划', '工作计划', '实施计划', '本计划', '该计划',
                        '加固改造工程',
                    }
                    if captured in generic_projects:
                        continue
                    # 排除跨行匹配
                    if '\n' in match_text:
                        continue
                    # 排除包含公司/机构后缀的碎片（属于公司名的一部分）
                    org_keywords = ('有限公司', '有限责任', '股份', '律师事务所', '会计师', '银行')
                    cap_start = match.start(1) if match.lastindex and match.lastindex >= 1 else start_pos
                    context_around = text[max(0, cap_start - 20):min(len(text), cap_start + len(captured) + 20)]
                    if any(kw in context_around for kw in org_keywords):
                        # 如果项目名词被公司名包裹，跳过
                        for kw in org_keywords:
                            if kw in context_around:
                                kw_pos = context_around.find(kw)
                                proj_pos = context_around.find(captured)
                                # 如果公司后缀和项目名之间没有明确分隔符（句号、逗号等），说明是连续文本
                                between = context_around[min(proj_pos + len(captured), kw_pos):max(proj_pos, kw_pos)]
                                if between and not any(c in between for c in '，。；、\n'):
                                    continue
                    # 使用捕获组作为实际匹配文本
                    match_text = captured
                    start_pos = match.start(1) if match.lastindex and match.lastindex >= 1 else start_pos
                    end_pos = start_pos + len(match_text)
                # 专利编号后处理：排除过短或明显非专利的匹配
                if pattern_name == 'patent_number':
                    if len(match_text) < 6:
                        continue
                # 门牌号后处理：排除"指导案例N号"/"检例第N号"等文书编号
                if pattern_name == 'house_number':
                    ctx_before = text[max(0, start_pos - 15):start_pos]
                    doc_num_kws = ('指导案例', '检例', '检例第', '案例第', '第', '公告', '通知', '决定', '规定', '条')
                    if any(kw in ctx_before for kw in doc_num_kws):
                        continue
                # 护照号后处理：P前缀容易误匹配文件编号/参考号
                if pattern_name == 'passport' and match_text[0] in 'Pp':
                    passport_ctx = text[max(0, start_pos - 50):min(len(text), end_pos + 50)]
                    passport_kws = ('护照', '出入境', '签证', 'passport', '证件号', '旅行证件')
                    if not any(kw in passport_ctx.lower() for kw in passport_kws):
                        continue
                filtered.append((match_text, pattern_name, start_pos))
                occupied.append((start_pos, end_pos))

        # 按位置排序
        filtered.sort(key=lambda x: x[2])
        return filtered

    def get_all_types(self) -> Dict[str, str]:
        """获取所有支持的类型及其描述"""
        return self.type_names.copy()
