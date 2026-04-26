#!/usr/bin/env python3
"""
生成《法律文档脱敏工具 - 首次使用指南》PDF
"""

import os
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ============ 字体注册 ============
def register_fonts():
    """注册中文字体"""
    font_paths = {
        'PingFang': [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
        ],
        'PingFangBold': [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Medium.ttc',
        ],
    }

    registered = False
    # macOS 字体
    for font_path in font_paths['PingFang']:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('PingFang', font_path, subfontIndex=0))
                pdfmetrics.registerFont(TTFont('PingFangBold', font_path, subfontIndex=1))
                registered = True
                break
            except Exception:
                continue

    if not registered:
        # Windows / Linux fallback
        fallback_fonts = [
            'C:/Windows/Fonts/msyh.ttc',      # 微软雅黑
            'C:/Windows/Fonts/simsun.ttc',     # 宋体
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        ]
        for font_path in fallback_fonts:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('PingFang', font_path, subfontIndex=0))
                    pdfmetrics.registerFont(TTFont('PingFangBold', font_path, subfontIndex=1))
                    registered = True
                    break
                except Exception:
                    continue

    if not registered:
        print("警告: 未找到中文字体，PDF可能无法正确显示中文")
        # 使用 Helvetica 作为回退
        pdfmetrics.registerFontFamily('PingFang', normal='Helvetica', bold='Helvetica-Bold')


register_fonts()


# ============ 颜色定义 ============
PRIMARY = HexColor('#1a5276')      # 深蓝
ACCENT = HexColor('#2980b9')       # 亮蓝
SUCCESS = HexColor('#27ae60')      # 绿色
WARNING = HexColor('#e67e22')      # 橙色
DANGER = HexColor('#c0392b')       # 红色
BG_LIGHT = HexColor('#f8f9fa')     # 浅灰背景
BG_BLUE = HexColor('#eaf2f8')      # 浅蓝背景
BORDER = HexColor('#bdc3c7')       # 边框灰
TEXT_DARK = HexColor('#2c3e50')    # 深色文字
TEXT_GRAY = HexColor('#7f8c8d')    # 灰色文字


# ============ 样式定义 ============
def create_styles():
    """创建PDF样式"""
    styles = {}

    styles['title'] = ParagraphStyle(
        'Title',
        fontName='PingFangBold',
        fontSize=24,
        textColor=PRIMARY,
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
        leading=32,
    )

    styles['subtitle'] = ParagraphStyle(
        'Subtitle',
        fontName='PingFang',
        fontSize=12,
        textColor=TEXT_GRAY,
        alignment=TA_CENTER,
        spaceAfter=15 * mm,
        leading=18,
    )

    styles['h1'] = ParagraphStyle(
        'H1',
        fontName='PingFangBold',
        fontSize=18,
        textColor=PRIMARY,
        spaceBefore=12 * mm,
        spaceAfter=6 * mm,
        leading=24,
        borderPadding=(0, 0, 2 * mm, 0),
    )

    styles['h2'] = ParagraphStyle(
        'H2',
        fontName='PingFangBold',
        fontSize=14,
        textColor=ACCENT,
        spaceBefore=8 * mm,
        spaceAfter=4 * mm,
        leading=20,
    )

    styles['h3'] = ParagraphStyle(
        'H3',
        fontName='PingFangBold',
        fontSize=12,
        textColor=TEXT_DARK,
        spaceBefore=5 * mm,
        spaceAfter=3 * mm,
        leading=17,
    )

    styles['body'] = ParagraphStyle(
        'Body',
        fontName='PingFang',
        fontSize=10.5,
        textColor=TEXT_DARK,
        alignment=TA_JUSTIFY,
        spaceAfter=3 * mm,
        leading=17,
        firstLineIndent=0,
    )

    styles['body_indent'] = ParagraphStyle(
        'BodyIndent',
        parent=styles['body'],
        leftIndent=8 * mm,
    )

    styles['bullet'] = ParagraphStyle(
        'Bullet',
        fontName='PingFang',
        fontSize=10.5,
        textColor=TEXT_DARK,
        spaceAfter=2 * mm,
        leading=17,
        leftIndent=8 * mm,
        bulletIndent=3 * mm,
    )

    styles['code'] = ParagraphStyle(
        'Code',
        fontName='Courier',
        fontSize=9.5,
        textColor=HexColor('#2d3436'),
        backColor=BG_LIGHT,
        spaceAfter=3 * mm,
        leading=15,
        leftIndent=8 * mm,
        rightIndent=8 * mm,
        borderPadding=(3 * mm, 3 * mm, 3 * mm, 3 * mm),
    )

    styles['tip'] = ParagraphStyle(
        'Tip',
        fontName='PingFang',
        fontSize=10,
        textColor=HexColor('#1e8449'),
        spaceAfter=3 * mm,
        leading=16,
        leftIndent=10 * mm,
        rightIndent=5 * mm,
    )

    styles['warning'] = ParagraphStyle(
        'Warning',
        fontName='PingFang',
        fontSize=10,
        textColor=HexColor('#a04000'),
        spaceAfter=3 * mm,
        leading=16,
        leftIndent=10 * mm,
        rightIndent=5 * mm,
    )

    styles['footer'] = ParagraphStyle(
        'Footer',
        fontName='PingFang',
        fontSize=8,
        textColor=TEXT_GRAY,
        alignment=TA_CENTER,
    )

    styles['toc'] = ParagraphStyle(
        'TOC',
        fontName='PingFang',
        fontSize=11,
        textColor=ACCENT,
        spaceAfter=3 * mm,
        leading=18,
        leftIndent=5 * mm,
    )

    return styles


# ============ 辅助函数 ============
def make_tip_box(text, styles, box_type='tip'):
    """创建提示框"""
    if box_type == 'tip':
        bg = HexColor('#e8f8f5')
        border_color = SUCCESS
        prefix = 'TIP'
    elif box_type == 'warning':
        bg = HexColor('#fef9e7')
        border_color = WARNING
        prefix = '注意'
    elif box_type == 'danger':
        bg = HexColor('#fdedec')
        border_color = DANGER
        prefix = '重要'
    else:
        bg = BG_BLUE
        border_color = ACCENT
        prefix = '说明'

    style = styles[box_type] if box_type in styles else styles['tip']
    content = Paragraph(f'<b>{prefix}:</b> {text}', style)

    t = Table([[content]], colWidths=[155 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('LEFTPADDING', (0, 0), (-1, -1), 4 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 3 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3 * mm),
    ]))
    return t


def make_step(number, title, description, styles):
    """创建步骤块"""
    num_style = ParagraphStyle(
        f'StepNum{number}',
        fontName='PingFangBold',
        fontSize=14,
        textColor=white,
        alignment=TA_CENTER,
        leading=18,
    )
    title_style = ParagraphStyle(
        f'StepTitle{number}',
        fontName='PingFangBold',
        fontSize=12,
        textColor=PRIMARY,
        leading=17,
    )
    desc_style = ParagraphStyle(
        f'StepDesc{number}',
        fontName='PingFang',
        fontSize=10.5,
        textColor=TEXT_DARK,
        leading=16,
    )

    num_para = Paragraph(str(number), num_style)
    title_para = Paragraph(title, title_style)
    desc_para = Paragraph(description, desc_style)

    t = Table(
        [[num_para, title_para], ['', desc_para]],
        colWidths=[12 * mm, 143 * mm],
        rowHeights=[8 * mm, None],
    )
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), ACCENT),
        ('ROUNDEDCORNERS', [3, 3, 3, 3]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * mm),
        ('LEFTPADDING', (1, 0), (1, -1), 4 * mm),
        ('SPAN', (0, 0), (0, 1)),
    ]))
    return t


# ============ 页面模板 ============
def on_page(canvas, doc):
    """页眉页脚"""
    canvas.saveState()
    # 页脚
    canvas.setFont('PingFang', 8)
    canvas.setFillColor(TEXT_GRAY)
    canvas.drawCentredString(A4[0] / 2, 12 * mm, f'- {doc.page} -')
    canvas.drawString(15 * mm, 12 * mm, '法律文档脱敏工具 by 黄灵宝同学')
    canvas.restoreState()


def on_first_page(canvas, doc):
    """首页无页眉"""
    canvas.saveState()
    canvas.setFont('PingFang', 8)
    canvas.setFillColor(TEXT_GRAY)
    canvas.drawCentredString(A4[0] / 2, 12 * mm, f'- {doc.page} -')
    canvas.restoreState()


# ============ 内容构建 ============
def build_content(styles):
    """构建PDF内容"""
    story = []

    # ===== 封面 =====
    story.append(Spacer(1, 40 * mm))
    story.append(Paragraph('法律文档脱敏工具', styles['title']))
    story.append(Paragraph('首次使用指南', ParagraphStyle(
        'SubTitle2', fontName='PingFangBold', fontSize=18,
        textColor=ACCENT, alignment=TA_CENTER, spaceAfter=8 * mm, leading=24,
    )))
    story.append(HRFlowable(width='60%', thickness=1, color=ACCENT,
                            spaceAfter=8 * mm, spaceBefore=3 * mm))
    story.append(Paragraph(
        '完全本地运行 | 不联网不上传 | 支持 30+ 种敏感信息自动识别',
        styles['subtitle']
    ))
    story.append(Spacer(1, 15 * mm))
    story.append(Paragraph(
        '适用于 macOS / Windows / Linux',
        ParagraphStyle('Platform', fontName='PingFang', fontSize=11,
                       textColor=TEXT_GRAY, alignment=TA_CENTER, leading=16)
    ))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        'by <b>黄灵宝同学</b>',
        ParagraphStyle('Author', fontName='PingFang', fontSize=12,
                       textColor=ACCENT, alignment=TA_CENTER, leading=16)
    ))

    story.append(PageBreak())

    # ===== 目录 =====
    story.append(Paragraph('目录', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))
    toc_items = [
        '一、产品简介',
        '二、安装准备',
        '三、快速启动（推荐）',
        '四、首次启动选项：是否处理英文文书',
        '五、手动安装（备选）',
        '六、使用方法 - 网页界面',
        '七、检测层级介绍：规则 + 中文 NER + 英文 LLM',
        '八、OCR 引擎：RapidOCR / PaddleOCR',
        '九、输出格式：MD / DOCX / PDF',
        '十、使用方法 - 命令行',
        '十一、支持的敏感信息类型',
        '十二、常见问题解答',
        '十三、隐私安全说明',
    ]
    for item in toc_items:
        story.append(Paragraph(item, styles['toc']))
    story.append(PageBreak())

    # ===== 一、产品简介 =====
    story.append(Paragraph('一、产品简介', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    story.append(Paragraph(
        '法律文档脱敏工具是一款<b>完全本地运行</b>的敏感信息脱敏软件，'
        '专为法律工作者设计。它能自动识别并替换文档中的个人信息、公司名称、'
        '案号、金额、地址等 30 余种敏感数据，确保文件在分享、归档或公开时不泄露隐私。',
        styles['body']
    ))

    story.append(Paragraph('核心特点', styles['h3']))

    features = [
        ['完全离线', '所有处理在本地完成，不调用任何外部 API，不上传任何数据'],
        ['多格式输入', '支持 PDF（含扫描版 OCR）、Word（DOCX/DOC）、TXT、Markdown、图片'],
        ['多格式输出', '一次脱敏同时生成 MD / DOCX / PDF 三份文件，按需选择'],
        ['原格式保留', 'DOCX→DOCX 完整保留字体/字号/页眉页脚；PDF→PDF 原地脱敏保留布局/盖章'],
        ['三层检测', '正则规则 + 中文 NER（CLUENER）+ 英文 LLM（OpenAI privacy-filter，可选）'],
        ['智能识别', '自动检测 30+ 种敏感信息：人名（含复姓）、公司、身份证、手机、银行卡、案号、地址等'],
        ['双 OCR 引擎', '默认 RapidOCR（快、轻量）；复杂排版可切 PaddleOCR（准、慢）'],
        ['灵活策略', '占位符替换（[PERSON_1]）/ 部分掩码（138****5678）两种模式'],
        ['冲突仲裁', '规则与 LLM 结果重叠时按 5 条规则智能仲裁，互相纠错'],
        ['同名扩展', '同一姓名在文档中所有出现位置自动一致脱敏'],
        ['自定义词典', '可手动添加/排除敏感词，适配特定文档需求'],
    ]

    for title, desc in features:
        story.append(Paragraph(
            f'<bullet>&bull;</bullet> <b>{title}</b> - {desc}',
            styles['bullet']
        ))

    # ===== 二、安装准备 =====
    story.append(Paragraph('二、安装准备', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    story.append(Paragraph('系统要求', styles['h3']))

    req_data = [
        ['项目', '要求'],
        ['操作系统', 'macOS 10.15+ / Windows 10+ / Linux'],
        ['Python', 'Python 3.9 或以上版本（推荐 3.11）'],
        ['磁盘空间', '基础约 1.5GB（含 PyTorch + venv）；'
                     '加中文 NER 模型 +400MB；加英文模型 +2.6GB'],
        ['内存', '建议 8GB 以上（加载 LLM 模型时占用约 3-4GB）'],
        ['浏览器', 'Chrome / Edge / Safari / Firefox（任选）'],
        ['网络', '首次启动需联网下载依赖和模型，之后完全离线运行'],
    ]
    req_table = Table(req_data, colWidths=[35 * mm, 120 * mm])
    req_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'PingFangBold'),
        ('FONTNAME', (0, 1), (-1, -1), 'PingFang'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3 * mm),
    ]))
    story.append(req_table)

    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph('检查 Python 是否已安装', styles['h3']))
    story.append(Paragraph(
        '<b>macOS:</b> 按 Command + 空格，搜索"终端"，打开后输入：',
        styles['body']
    ))
    story.append(Paragraph('python3 --version', styles['code']))
    story.append(Paragraph(
        '<b>Windows:</b> 按 Win + R，输入 cmd 回车，然后输入：',
        styles['body']
    ))
    story.append(Paragraph('python --version', styles['code']))
    story.append(Paragraph(
        '如果显示 Python 3.x.x（如 Python 3.11.3），说明已安装。'
        '如果提示"未找到命令"，请从 python.org 下载安装。',
        styles['body']
    ))
    story.append(make_tip_box(
        'Windows 安装 Python 时<b>务必勾选</b> "Add Python to PATH"（安装界面最下方的复选框），'
        '否则在命令行中无法使用 python 命令。',
        styles, 'warning'
    ))

    # ===== 三、快速启动 =====
    story.append(PageBreak())
    story.append(Paragraph('三、快速启动（推荐）', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    story.append(Paragraph(
        '这是最简单的启动方式，仅需两步：解压 + 双击。',
        styles['body']
    ))

    story.append(Paragraph('macOS 用户', styles['h2']))

    story.append(make_step(1, '解压文件',
        '将下载的 legal-anonymizer.zip 解压到任意位置（如桌面）',
        styles))
    story.append(Spacer(1, 3 * mm))
    story.append(make_step(2, '双击启动',
        '双击文件夹中的<b>【请双击我！】启动脱敏工具.command</b>。'
        '首次运行会自动安装依赖，完成后会自动打开浏览器。',
        styles))

    story.append(Spacer(1, 5 * mm))
    story.append(make_tip_box(
        '首次打开可能弹出 macOS 安全提示"无法验证开发者"。'
        '请打开<b>系统设置 > 隐私与安全性</b>，向下滚动找到被阻止的提示，'
        '点击<b>"仍要打开"</b>，输入密码确认即可。之后再次双击就不会再弹提示。',
        styles, 'warning'
    ))

    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph('Windows 用户', styles['h2']))

    story.append(make_step(1, '解压文件',
        '右键 legal-anonymizer.zip，选择"全部解压缩"',
        styles))
    story.append(Spacer(1, 3 * mm))
    story.append(make_step(2, '双击启动',
        '双击文件夹中的<b>启动脱敏工具.bat</b>',
        styles))

    # ===== 四、首次启动选项 =====
    story.append(PageBreak())
    story.append(Paragraph('四、首次启动选项：是否处理英文文书', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    story.append(Paragraph(
        '首次双击启动脚本时，工具会询问您一个问题：',
        styles['body']
    ))
    story.append(make_tip_box(
        '<b>"您是否经常处理英文/涉外法律文书？(y / n)"</b>',
        styles, 'info'
    ))
    story.append(Paragraph(
        '这是为了决定是否启用英文识别能力（基于 OpenAI privacy-filter 模型）。'
        '工具默认能识别中文文档里的所有敏感信息，'
        '英文识别只对涉外律师有用。',
        styles['body']
    ))

    story.append(Paragraph('选择 "y"（是）—— 启用英文识别', styles['h3']))
    en_yes = [
        '能识别英文人名（如 John Smith）、英文地址、国际电话、API 密钥',
        '首次勾选 OpenAI 开关时会下载约 <b>2.6 GB</b> 模型（一次性）',
        '适合涉外仲裁、跨境合同、外资企业法律事务',
    ]
    for p in en_yes:
        story.append(Paragraph(f'<bullet>&bull;</bullet> {p}', styles['bullet']))

    story.append(Paragraph('选择 "n"（否）—— 仅中文模式', styles['h3']))
    en_no = [
        '只识别中文 PII，但中文文档准确率已接近 100%',
        '<b>节省 2.6 GB 磁盘空间和首次下载时间</b>',
        '适合绝大多数中国律师场景（合同/判决书/答辩状均纯中文）',
        '网页界面将不显示 OpenAI 开关',
    ]
    for p in en_no:
        story.append(Paragraph(f'<bullet>&bull;</bullet> {p}', styles['bullet']))

    story.append(make_tip_box(
        '<b>选错了想反悔？</b>删除项目根目录下的 <code>.user_config</code> 文件，'
        '重新双击启动脚本即可重新选择。',
        styles, 'tip'
    ))

    # ===== 五、手动安装 =====
    story.append(PageBreak())
    story.append(Paragraph('五、手动安装（备选）', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    story.append(Paragraph(
        '如果快速启动不生效，可以手动安装。',
        styles['body']
    ))

    story.append(make_step(1, '打开终端/命令行',
        '<b>macOS:</b> Command + 空格 > 搜索"终端"<br/>'
        '<b>Windows:</b> Win + R > 输入 cmd > 回车',
        styles))
    story.append(Spacer(1, 3 * mm))

    story.append(make_step(2, '进入项目文件夹',
        '在终端输入 cd ，然后将文件夹从访达/资源管理器拖到终端窗口，按回车。<br/>'
        '或直接输入路径，例如：cd ~/Desktop/legal-anonymizer',
        styles))
    story.append(Spacer(1, 3 * mm))

    story.append(make_step(3, '安装依赖（仅首次）',
        '<b>macOS:</b> pip3 install -r requirements.txt<br/>'
        '<b>Windows:</b> pip install -r requirements.txt<br/>'
        '等待安装完成，无红色报错即可。',
        styles))
    story.append(Spacer(1, 3 * mm))

    story.append(make_step(4, '启动工具',
        '<b>macOS:</b> python3 web_app.py<br/>'
        '<b>Windows:</b> python web_app.py<br/>'
        '启动后会自动打开浏览器。如未自动打开，手动访问终端显示的地址（通常是 http://127.0.0.1:8080）',
        styles))

    story.append(Spacer(1, 5 * mm))
    story.append(make_tip_box(
        '不要关闭终端窗口！关闭终端 = 停止服务。使用完毕后再关闭。',
        styles, 'danger'
    ))

    # ===== 六、使用方法 - 网页界面 =====
    story.append(PageBreak())
    story.append(Paragraph('六、使用方法 - 网页界面', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    story.append(Paragraph('基本流程', styles['h2']))

    story.append(make_step(1, '上传文件',
        '将文件拖拽到网页上传区域，或点击选择文件。支持 PDF、DOCX、TXT 格式。<br/>'
        '也可以将文件放入项目文件夹下的 inbox 目录，在页面中直接选择。',
        styles))
    story.append(Spacer(1, 3 * mm))

    story.append(make_step(2, '自动分析',
        '上传后工具会自动扫描文档，列出所有识别到的敏感信息。'
        '每项旁边有复选框，可以取消勾选不需要脱敏的项目。',
        styles))
    story.append(Spacer(1, 3 * mm))

    story.append(make_step(3, '手动补充（可选）',
        '如果发现有遗漏的敏感信息，可以手动添加到自定义词典。'
        '词典会持久保存，下次使用时自动生效。',
        styles))
    story.append(Spacer(1, 3 * mm))

    story.append(make_step(4, '执行脱敏',
        '点击"执行脱敏"按钮，等待处理完成后下载脱敏结果文件。<br/>'
        '同时会生成映射表（JSON），记录每个占位符对应的原始内容。',
        styles))

    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph('脱敏策略说明', styles['h2']))

    strategy_data = [
        ['策略', '效果示例', '适用场景'],
        ['占位符替换', '张三 > [PERSON_1]', '完全隐藏原始信息，适合公开发布'],
        ['部分掩码', '138****5678', '保留部分信息便于核对，适合内部使用'],
    ]
    strategy_table = Table(strategy_data, colWidths=[30 * mm, 60 * mm, 65 * mm])
    strategy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'PingFangBold'),
        ('FONTNAME', (0, 1), (-1, -1), 'PingFang'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3 * mm),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(strategy_table)

    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph('继续脱敏功能', styles['h2']))
    story.append(Paragraph(
        '第一次脱敏后，如果发现仍有遗漏的敏感信息，可以使用"继续脱敏"功能：'
        '手动添加遗漏的词条，工具会基于原始文本重新处理，'
        '新添加的词条也会自动存入词典供后续使用。',
        styles['body']
    ))

    # ===== 七、检测层级介绍 =====
    story.append(PageBreak())
    story.append(Paragraph('七、检测层级介绍：规则 + 中文 NER + 英文 LLM', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    story.append(Paragraph(
        '本工具采用<b>三层检测架构</b>，每层负责不同类型的敏感信息，'
        '协同工作互相纠错。这是它准确率高的核心原因。',
        styles['body']
    ))

    layer_data = [
        ['层级', '负责检测', '速度'],
        ['正则规则', '身份证、手机、邮箱、案号、信用代码等 30+ 结构化数据', '极快（毫秒级）'],
        ['中文 NER（CLUENER）', '中文人名（含复姓）、公司名、律所、地址、机构', '快（秒级）'],
        ['英文 LLM（OpenAI，可选）', '英文人名、英文地址、国际电话、API 密钥', '稍慢（数秒）'],
    ]
    layer_table = Table(layer_data, colWidths=[40 * mm, 90 * mm, 25 * mm])
    layer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'PingFangBold'),
        ('FONTNAME', (0, 1), (-1, -1), 'PingFang'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3 * mm),
    ]))
    story.append(layer_table)

    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph('网页界面的检测层开关', styles['h3']))
    story.append(Paragraph(
        '在网页上传区域下方有两个（或三个）开关：',
        styles['body']
    ))
    switch_points = [
        '<b>启用 OCR</b>——扫描版 PDF / 图片必开；非扫描 PDF 可选',
        '<b>中文 NER</b>——所有中文文书<b>都建议开启</b>，能补正则的盲区',
        '<b>OpenAI privacy-filter</b>——仅在首次启动选择"是"时显示，处理英文文书时勾选',
    ]
    for p in switch_points:
        story.append(Paragraph(f'<bullet>&bull;</bullet> {p}', styles['bullet']))

    # ===== 八、OCR 引擎 =====
    story.append(PageBreak())
    story.append(Paragraph('八、OCR 引擎：RapidOCR / PaddleOCR', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    story.append(Paragraph(
        '当输入是扫描版 PDF 或图片时，工具会用 OCR 引擎把图像转为文字。'
        '内置两个引擎：',
        styles['body']
    ))

    ocr_data = [
        ['引擎', '速度（每页）', '准确度', '体积', '默认'],
        ['RapidOCR', '约 2 秒', '良好', '15 MB', '✓'],
        ['PaddleOCR 3.5', '约 30 秒', '稍优（复杂排版）', '约 200 MB', ''],
    ]
    ocr_table = Table(ocr_data, colWidths=[35 * mm, 30 * mm, 40 * mm, 25 * mm, 15 * mm])
    ocr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'PingFangBold'),
        ('FONTNAME', (0, 1), (-1, -1), 'PingFang'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3 * mm),
        ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(ocr_table)

    story.append(Spacer(1, 5 * mm))
    story.append(make_tip_box(
        '<b>什么时候切到 PaddleOCR？</b>'
        'RapidOCR 默认情况下识别得已经很好。如果你发现某份扫描版 PDF 错字特别多'
        '（比如盖章、糊字、表格复杂），勾选 OCR 后再勾"PaddleOCR"重新分析一次。',
        styles, 'tip'
    ))

    # ===== 九、输出格式 =====
    story.append(PageBreak())
    story.append(Paragraph('九、输出格式：MD / DOCX / PDF', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    story.append(Paragraph(
        '工具支持<b>同时输出三种格式</b>。在网页脱敏页面，"输出格式"那里有三个复选框，'
        '可以全选，也可以只勾你需要的。',
        styles['body']
    ))

    out_data = [
        ['格式', '保留原格式', '适用场景'],
        ['MD（Markdown）', '×', '快速预览、复制粘贴、导入笔记软件'],
        ['DOCX（Word）', '✓ 输入 DOCX 时完整保留字体/字号/排版', '律师工作底稿、案件归档、给客户'],
        ['PDF', '✓ 输入 PDF 时原地脱敏，保留布局/盖章/签名', '正式文件、法庭证据、对外交付'],
    ]
    out_table = Table(out_data, colWidths=[30 * mm, 65 * mm, 60 * mm])
    out_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'PingFangBold'),
        ('FONTNAME', (0, 1), (-1, -1), 'PingFang'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3 * mm),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(out_table)

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        '<b>原格式保留是什么意思？</b>—— 比如你输入一份 Word 合同（标楷体小四 1.5 倍行距），'
        '输出的 DOCX 文件还是标楷体小四 1.5 倍行距，只是当事人姓名变成了占位符。'
        '同理 PDF 输入会得到一份保留所有布局/字体/盖章的脱敏版 PDF。',
        styles['body']
    ))

    story.append(make_tip_box(
        '<b>跨格式输出（如 PDF→DOCX）</b>：会用<b>仿宋小四 1.5 倍行距</b>'
        '（法律文书标准模板）重新排版。',
        styles, 'info'
    ))

    # ===== 十、使用方法 - 命令行 =====
    story.append(PageBreak())
    story.append(Paragraph('十、使用方法 - 命令行', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    story.append(Paragraph(
        '命令行适合批量处理或集成到工作流中。',
        styles['body']
    ))

    cmd_examples = [
        ('脱敏 Word 文档（保留原格式）', 'python3 cli.py anonymize input.docx -o output.docx --cn-llm'),
        ('脱敏 PDF（PDF 原地脱敏）', 'python3 cli.py anonymize input.pdf -o output.pdf --cn-llm'),
        ('一次输出 MD+DOCX+PDF 三种格式', 'python3 cli.py anonymize input.pdf -o output -f md,docx,pdf --cn-llm'),
        ('扫描版 PDF（启用 OCR + 中文 NER）', 'python3 cli.py anonymize scan.pdf -o output.docx --ocr --cn-llm'),
        ('扫描版用 PaddleOCR 引擎', 'python3 cli.py anonymize scan.pdf -o out.docx --ocr --ocr-engine paddleocr'),
        ('全开模式（中英混合涉外案件）', 'python3 cli.py anonymize input.pdf -o out.pdf --cn-llm --llm'),
        ('只分析不脱敏', 'python3 cli.py analyze input.docx --cn-llm'),
        ('查看所有支持的类型', 'python3 cli.py list-types'),
        ('只脱敏手机号和邮箱', 'python3 cli.py anonymize input.pdf --only phone,email'),
        ('使用部分掩码策略', 'python3 cli.py anonymize input.pdf --mask-strategy partial'),
    ]

    for desc, cmd in cmd_examples:
        story.append(Paragraph(f'<b>{desc}:</b>', styles['body']))
        story.append(Paragraph(cmd, styles['code']))

    # ===== 十一、支持的敏感信息类型 =====
    story.append(PageBreak())
    story.append(Paragraph('十一、支持的敏感信息类型', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    story.append(Paragraph(
        '工具支持自动识别以下 30+ 种敏感信息：',
        styles['body']
    ))

    type_data = [
        ['类别', '包含类型'],
        ['身份证件', '身份证号、护照号、港澳通行证、台湾通行证、军官证'],
        ['企业/机构', '统一社会信用代码、组织机构代码、税务登记号、公司名、律所名'],
        ['案件/合同', '案号、合同编号、发票号码、文件编号'],
        ['联系方式', '手机号、座机/传真、400/800 电话、邮箱、网址'],
        ['社交账号', 'QQ 号、微信号'],
        ['金融信息', '银行卡号、人民币金额（含中文大写）、外币金额'],
        ['车辆信息', '车牌号、车辆识别码（VIN）'],
        ['地址信息', '完整地址、邮政编码、门牌号'],
        ['人名', '基于上下文关键词自动识别法律文书中的人名'],
        ['机构名称', '公司、律所、法院、政府机构、银行、学校、医院等'],
        ['日期时间', '日期、时间、日期时间'],
        ['网络标识', 'IP 地址、MAC 地址'],
        ['证书编号', '房地产证号、证书/批文编号、专利/商标编号'],
        ['项目名称', '项目、工程、系统、平台名称'],
    ]

    type_table = Table(type_data, colWidths=[28 * mm, 127 * mm])
    type_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'PingFangBold'),
        ('FONTNAME', (0, 1), (-1, -1), 'PingFang'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3 * mm),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(type_table)

    # ===== 十二、常见问题解答 =====
    story.append(PageBreak())
    story.append(Paragraph('十二、常见问题解答', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    faqs = [
        ('pip install 报错 Permission denied',
         '在命令前加 --user：pip3 install --user -r requirements.txt'),
        ('启动后浏览器没有自动打开',
         '手动打开浏览器，输入终端中显示的地址（通常是 http://127.0.0.1:8080）。'),
        ('启动报错 Address already in use',
         '端口被占用，程序会自动尝试 8080-8099 端口。如果都被占用，关掉其他程序后重试。'),
        ('Windows 上 python 命令打开 Microsoft Store',
         '在系统设置中关闭"应用执行别名"中的 Python 项，或使用完整路径运行。'),
        ('macOS 提示 command not found: python3',
         '需要安装 Python。或尝试安装 Xcode 命令行工具：xcode-select --install'),
        ('报错 ModuleNotFoundError',
         '依赖未安装成功，重新执行 pip 安装命令。确保 pip 和 python 版本一致：python3 -m pip install -r requirements.txt'),
        ('我之前选了不安装英文模型，现在想用了怎么办',
         '删除项目根目录下的 .user_config 文件，重新双击启动脚本，会再次询问。选择"y"即启用英文识别。'),
        ('国内下载模型很慢',
         '启动脚本默认走 hf-mirror.com 国内镜像。如果还慢，可以手动设置环境变量：export HF_ENDPOINT=https://hf-mirror.com'),
        ('勾选"中文 NER"后第一次分析等了很久',
         '正常现象。首次启用会从 HuggingFace 下载约 400MB 模型，国内 1-3 分钟。下完后所有后续操作都是秒级。'),
        ('网页里没有 OpenAI 开关',
         '说明你首次启动时选择了"仅中文模式"。删除 .user_config 重启即可重新选择。'),
        ('DOCX 输出格式和原文不一样',
         '当输入是 DOCX 且输出也是 DOCX 时，工具会自动保留原始格式。如果输入是 PDF，输出的 DOCX 用仿宋小四 1.5 倍行距标准模板。'),
        ('PDF 输出和原 PDF 长得不一样',
         '当输入是 PDF 且输出也是 PDF 时，会做"原地脱敏"——保留原 PDF 的字体、布局、盖章、签名，只把敏感字替换为占位符。'),
        ('OCR 识别错字多',
         '默认 RapidOCR 已经够用。复杂排版可在勾选"启用 OCR"后切到"PaddleOCR"引擎重新分析（更慢但稍准）。'),
        ('扫描版 PDF 识别不了文字',
         '勾选"启用 OCR"开关。RapidOCR 引擎已内置，无需额外安装。首次使用会自动下载约 15MB 模型。'),
        ('某些敏感信息没有被识别到',
         '一是开启"中文 NER"层（强烈建议）；二是用网页"用户词典"功能手动添加，词典会持久保存。'),
        ('脱敏后想反向查回原文',
         '每次脱敏会生成一份 _mapping.json 映射表，包含占位符与原文的对应关系。请像对待原文件一样妥善保管。'),
    ]

    for q, a in faqs:
        story.append(Paragraph(f'<b>Q: {q}</b>', styles['body']))
        story.append(Paragraph(f'A: {a}', styles['body_indent']))
        story.append(Spacer(1, 2 * mm))

    # ===== 十三、隐私安全说明 =====
    story.append(Paragraph('十三、隐私安全说明', styles['h1']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5 * mm))

    story.append(make_tip_box(
        '本工具所有处理<b>完全在本地</b>进行，<b>不调用任何外部 API</b>，<b>不上传任何数据</b>到云端。'
        '代码完全开源可审计，适合处理高度机密的法律文件。',
        styles, 'tip'
    ))

    story.append(Spacer(1, 5 * mm))

    security_points = [
        '所有文本分析和替换在内存中完成，不经过网络传输',
        '所有 AI 模型（中文 NER / OpenAI / RapidOCR / PaddleOCR）首次下载后完全离线运行，'
        '不需要联网',
        '上传的文件会在处理完成后自动清理（网页模式下 24 小时后删除）',
        '生成的映射表（_mapping.json）包含原始敏感信息与占位符的对应关系，请妥善保管',
        '建议在处理完成后删除映射文件，或将其存放在安全的位置',
        '工具源码完全开源可审计，可执行 grep -r "requests|urllib|http" *.py 验证'
        '项目代码本身零网络调用',
        '可设置三个环境变量进一步彻底断网：HF_HUB_OFFLINE=1、TRANSFORMERS_OFFLINE=1、'
        'PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=1',
    ]
    for point in security_points:
        story.append(Paragraph(
            f'<bullet>&bull;</bullet> {point}',
            styles['bullet']
        ))

    story.append(Spacer(1, 10 * mm))
    story.append(make_tip_box(
        '<b>映射表安全提示：</b>脱敏后生成的 _mapping.json 文件包含所有原始敏感信息的对应关系。'
        '请像对待原文件一样妥善保管此文件，不要随脱敏版文件一起分享。',
        styles, 'danger'
    ))

    story.append(Spacer(1, 20 * mm))
    story.append(HRFlowable(width='40%', thickness=0.5, color=BORDER,
                            spaceAfter=5 * mm, spaceBefore=5 * mm))
    story.append(Paragraph(
        '如有问题或建议，欢迎反馈。祝使用愉快！',
        ParagraphStyle('EndNote', fontName='PingFang', fontSize=11,
                       textColor=TEXT_GRAY, alignment=TA_CENTER, leading=16)
    ))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(
        'Made with love by <b>黄灵宝同学</b>',
        ParagraphStyle('Brand', fontName='PingFang', fontSize=10,
                       textColor=ACCENT, alignment=TA_CENTER, leading=14)
    ))

    return story


# ============ 主入口 ============
def main():
    output_path = Path(__file__).parent / '首次使用指南.pdf'

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title='法律文档脱敏工具 - 首次使用指南',
        author='Legal Anonymizer',
    )

    styles = create_styles()
    story = build_content(styles)

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_page)
    print(f'PDF 生成成功: {output_path}')


if __name__ == '__main__':
    main()
