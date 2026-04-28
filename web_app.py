#!/usr/bin/env python3
"""
Legal Document Anonymizer - Web UI
法律文档脱敏工具 - Web 界面

Usage:
    python3 web_app.py
    # Open http://127.0.0.1:5000
"""

import os
# 禁用 PaddleOCR 启动时的网络连通性检测（会阻塞数十秒）
os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')

import sys
import re
import json
import uuid
import time
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Optional

# 确保模块路径
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify, send_file, render_template
from anonymizer import LegalAnonymizer


def is_scanned_pdf(file_path: str) -> bool:
    """检测PDF是否为扫描版（文本内容极少）"""
    try:
        import fitz
        doc = fitz.open(file_path)
        total_text = 0
        for page in doc:
            total_text += len(page.get_text().strip())
            if total_text > 100:
                doc.close()
                return False
        doc.close()
        return True
    except Exception:
        return False

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# 目录配置
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = BASE_DIR / 'output'
INBOX_DIR = BASE_DIR / 'inbox'
USER_DICT_PATH = BASE_DIR / 'user_dict.json'

for d in [UPLOAD_DIR, OUTPUT_DIR, INBOX_DIR]:
    d.mkdir(exist_ok=True)


def load_user_dict() -> list:
    """加载持久化用户词典"""
    if USER_DICT_PATH.exists():
        try:
            with open(USER_DICT_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_user_dict(entries: list):
    """保存用户词典到磁盘"""
    with open(USER_DICT_PATH, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

# 支持的文件格式
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.md', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp'}

# 会话存储（内存，单用户本地使用）
sessions: Dict[str, dict] = {}

# 会话超时时间（2小时）
SESSION_TIMEOUT = 7200


def cleanup_sessions():
    """清理过期会话"""
    now = time.time()
    expired = [sid for sid, s in sessions.items() if now - s['created_at'] > SESSION_TIMEOUT]
    for sid in expired:
        _cleanup_session_files(sid)
        del sessions[sid]


def _cleanup_session_files(session_id: str):
    """清理会话相关文件"""
    session = sessions.get(session_id)
    if not session:
        return
    # 清理上传文件（仅清理从 inbox 复制过来的副本）
    upload_path = session.get('upload_path')
    if upload_path and Path(upload_path).exists() and str(UPLOAD_DIR) in str(upload_path):
        try:
            Path(upload_path).unlink()
        except Exception:
            pass


def create_session(file_path: str, file_name: str) -> dict:
    """创建新会话"""
    cleanup_sessions()

    session_id = str(uuid.uuid4())[:8]
    suffix = Path(file_name).suffix.lower()

    session = {
        'id': session_id,
        'created_at': time.time(),
        'file_path': file_path,
        'file_name': file_name,
        'file_type': suffix,
        'is_pdf': suffix == '.pdf',
        'is_image': suffix in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp'},
        'file_size': os.path.getsize(file_path),
        'text': None,
        'findings': None,
        'custom_entities': [],
        'use_ocr': False,
        'ocr_engine': 'rapidocr',
        'use_cn_llm': False,
        'use_llm': False,
        'output_path': None,
        'output_format': None,
        'result': None,
    }
    sessions[session_id] = session
    return session


# ==================== 页面路由 ====================

@app.route('/')
def index():
    # 启动脚本根据用户首次选择写入 ENABLE_OPENAI=0/1，未启用时前端隐藏 OpenAI 开关
    enable_openai = os.environ.get('ENABLE_OPENAI', '0') == '1'
    return render_template('index.html', enable_openai=enable_openai)


# ==================== API 路由 ====================

@app.route('/api/types', methods=['GET'])
def get_types():
    """获取所有支持的实体类型"""
    anonymizer = LegalAnonymizer()
    types = anonymizer.get_supported_types()
    # 补充自动检测类型
    auto_types = {
        'person': '人名',
        'company': '公司名',
        'law_firm': '律师事务所',
        'court': '法院',
        'government': '政府机关',
        'institution': '机构',
        'bank_name': '银行',
        'address': '地址',
        'other': '其他',
    }
    types.update(auto_types)
    return jsonify({'types': types})


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件"""
    if 'file' not in request.files:
        return jsonify({'error': '未选择文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '文件名为空'}), 400

    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return jsonify({'error': f'不支持的文件格式: {suffix}'}), 400

    # 保存上传文件
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = UPLOAD_DIR / safe_name
    file.save(str(save_path))

    session = create_session(str(save_path), file.filename)

    # 检测扫描版PDF
    is_scanned = False
    if session['is_pdf']:
        is_scanned = is_scanned_pdf(str(save_path))

    return jsonify({
        'session_id': session['id'],
        'file_name': session['file_name'],
        'file_type': session['file_type'],
        'file_size': session['file_size'],
        'is_pdf': session['is_pdf'],
        'is_image': session['is_image'],
        'is_scanned': is_scanned,
    })


@app.route('/api/inbox', methods=['GET'])
def list_inbox():
    """列出 inbox 文件夹中的文件"""
    files = []
    for f in sorted(INBOX_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS and not f.name.startswith('.'):
            stat = f.stat()
            files.append({
                'name': f.name,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'type': f.suffix.lower(),
                'is_pdf': f.suffix.lower() == '.pdf',
            })
    return jsonify({
        'files': files,
        'inbox_path': str(INBOX_DIR),
    })


@app.route('/api/inbox/select', methods=['POST'])
def select_inbox_file():
    """从 inbox 选择文件"""
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': '未指定文件名'}), 400

    source_path = INBOX_DIR / filename
    if not source_path.exists():
        return jsonify({'error': '文件不存在'}), 404

    # 复制到 uploads（不修改原文件）
    safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    dest_path = UPLOAD_DIR / safe_name
    shutil.copy2(str(source_path), str(dest_path))

    session = create_session(str(dest_path), filename)

    # 检测扫描版PDF
    is_scanned = False
    if session['is_pdf']:
        is_scanned = is_scanned_pdf(str(dest_path))

    return jsonify({
        'session_id': session['id'],
        'file_name': session['file_name'],
        'file_type': session['file_type'],
        'file_size': session['file_size'],
        'is_pdf': session['is_pdf'],
        'is_image': session['is_image'],
        'is_scanned': is_scanned,
    })


def _run_single_analyze(session_id: str, use_ocr: bool, ocr_engine: str,
                         use_cn_llm: bool, use_llm: bool):
    """后台线程跑单文件 OCR + 检测，期间更新 session['analyze_progress']"""
    session = sessions.get(session_id)
    if not session:
        return
    progress = session['analyze_progress']
    progress['stage'] = 'ocr'
    progress['started_at'] = time.time()

    # 计算 ETA：扫描版按页数预估，文字版很快
    fp = session['file_path']
    progress['eta_s'] = _estimate_eta(fp, use_ocr) if Path(fp).suffix.lower() == '.pdf' else 5.0

    def on_progress(stage, current, total):
        progress['stage'] = stage
        progress['current'] = current
        progress['total'] = max(total, 1)
        progress['percent'] = round(current / max(total, 1) * 90, 1)  # OCR 占总流程 90%

    try:
        anonymizer = LegalAnonymizer(use_cn_llm=use_cn_llm, use_llm=use_llm)
        ud = load_user_dict()
        if ud:
            anonymizer.add_custom_entities(ud)

        text = anonymizer.processor.extract_text(
            fp, use_ocr=use_ocr, ocr_engine=ocr_engine, progress_callback=on_progress,
        )
        session['text'] = text
        if not text.strip():
            progress['stage'] = 'error'
            progress['error'] = '文件内容为空，如果是扫描版 PDF 请启用 OCR'
            progress['percent'] = 100
            return

        progress['stage'] = 'detect'
        progress['percent'] = 92
        all_entities = anonymizer._detect_all(text)
        session['auto_entities'] = all_entities

        # 整理 findings
        CONTEXT_WINDOW = 40
        findings, seen = {}, {}
        for entity_text, entity_type, pos in all_entities:
            key = (entity_text, entity_type)
            if key not in seen:
                start = max(0, pos - CONTEXT_WINDOW)
                end = min(len(text), pos + len(entity_text) + CONTEXT_WINDOW)
                seen[key] = text[start:end].replace('\n', ' ').strip()
            findings.setdefault(entity_type, [])
            if not any(it['text'] == entity_text for it in findings[entity_type]):
                findings[entity_type].append({'text': entity_text, 'context': seen[key]})
        session['findings'] = findings

        type_names = anonymizer.pattern_detector.type_names.copy()
        type_names.update({
            'person': '人名', 'company': '公司名', 'law_firm': '律师事务所',
            'court': '法院', 'government': '政府机关', 'institution': '机构',
            'bank_name': '银行', 'address': '地址',
        })
        progress['result'] = {
            'findings': findings,
            'total_findings': len(all_entities),
            'type_count': len(findings),
            'type_names': type_names,
            'text_preview': text[:500] + ('...' if len(text) > 500 else ''),
        }
        progress['stage'] = 'done'
        progress['percent'] = 100
        progress['finished_at'] = time.time()
        progress['elapsed_s'] = round(progress['finished_at'] - progress['started_at'], 1)
    except Exception as e:
        import traceback; traceback.print_exc()
        progress['stage'] = 'error'
        progress['error'] = str(e)
        progress['percent'] = 100


@app.route('/api/analyze', methods=['POST'])
def analyze_document():
    """启动单文件分析（异步）。调用后立即返回，前端轮询 /api/analyze/status"""
    data = request.get_json()
    session_id = data.get('session_id')
    use_ocr = data.get('use_ocr', False)
    ocr_engine = data.get('ocr_engine', 'rapidocr')
    use_cn_llm = data.get('use_cn_llm', False)
    use_llm = data.get('use_llm', False)

    session = sessions.get(session_id)
    if not session:
        return jsonify({'error': '会话不存在或已过期'}), 404

    session['use_ocr'] = use_ocr
    session['ocr_engine'] = ocr_engine
    session['use_cn_llm'] = use_cn_llm
    session['use_llm'] = use_llm
    session['analyze_progress'] = {
        'stage': 'queued', 'percent': 0, 'current': 0, 'total': 0,
        'eta_s': 0, 'started_at': 0, 'finished_at': 0, 'elapsed_s': 0,
        'error': None, 'result': None,
    }

    threading.Thread(
        target=_run_single_analyze,
        args=(session_id, use_ocr, ocr_engine, use_cn_llm, use_llm),
        daemon=True,
    ).start()
    return jsonify({'status': 'started', 'session_id': session_id})


@app.route('/api/analyze/status/<session_id>', methods=['GET'])
def analyze_status(session_id):
    """查询单文件分析进度"""
    session = sessions.get(session_id)
    if not session or 'analyze_progress' not in session:
        return jsonify({'error': '会话不存在或未开始分析'}), 404
    p = session['analyze_progress']
    now = time.time()
    payload = {
        'stage': p['stage'],
        'percent': p['percent'],
        'current': p.get('current', 0),
        'total': p.get('total', 0),
        'eta_s': p.get('eta_s', 0),
        'started_at': p.get('started_at', 0),
        'elapsed_s': p.get('elapsed_s', 0) if p['stage'] in ('done', 'error')
                     else (round(now - p['started_at'], 1) if p.get('started_at') else 0),
        'error': p.get('error'),
        'now': now,
    }
    if p['stage'] == 'done':
        payload['result'] = p.get('result')
    return jsonify(payload)




@app.route('/api/entities', methods=['POST'])
def manage_entities():
    """管理自定义实体"""
    data = request.get_json()
    session_id = data.get('session_id')
    action = data.get('action', 'add')  # add, remove, set

    session = sessions.get(session_id)
    if not session:
        return jsonify({'error': '会话不存在或已过期'}), 404

    entities = data.get('entities', [])

    if action == 'set':
        session['custom_entities'] = entities
    elif action == 'add':
        for entity in entities:
            if entity not in session['custom_entities']:
                session['custom_entities'].append(entity)
    elif action == 'remove':
        for entity in entities:
            if entity in session['custom_entities']:
                session['custom_entities'].remove(entity)

    return jsonify({
        'custom_entities': session['custom_entities'],
        'count': len(session['custom_entities']),
    })


@app.route('/api/anonymize', methods=['POST'])
def anonymize_document():
    """执行脱敏"""
    data = request.get_json()
    session_id = data.get('session_id')
    output_format = data.get('output_format', 'docx')
    mask_strategy = data.get('mask_strategy', 'placeholder')
    excluded_entities = data.get('excluded_entities', [])  # [{type, name}]

    session = sessions.get(session_id)
    if not session:
        return jsonify({'error': '会话不存在或已过期'}), 404

    if not session.get('text'):
        return jsonify({'error': '请先分析文档'}), 400

    try:
        anonymizer = LegalAnonymizer(
            use_cn_llm=session.get('use_cn_llm', False),
            use_llm=session.get('use_llm', False),
        )

        # 设置掩码策略；whitebox 是占位符策略 + PDF 渲染时不画文字
        pdf_whitebox = (mask_strategy == 'whitebox')
        effective_strategy = 'placeholder' if pdf_whitebox else mask_strategy
        if effective_strategy:
            anonymizer.set_all_mask_strategy(effective_strategy)

        # 占位符风格（中文/英文）—— 仅在 placeholder/whitebox 模式下生效
        placeholder_style = data.get('placeholder_style', 'english_bracket')
        anonymizer.set_placeholder_style(placeholder_style)

        # 注入用户词典 + 会话自定义实体
        user_dict = load_user_dict()
        if user_dict:
            anonymizer.add_custom_entities(user_dict)
        if session['custom_entities']:
            anonymizer.add_custom_entities(session['custom_entities'])

        # 重新检测实体
        all_entities = anonymizer._detect_all(session['text'])

        # 过滤掉用户排除的实体
        if excluded_entities:
            excluded_set = {(e['type'], e['name']) for e in excluded_entities}
            all_entities = [
                (text, etype, pos) for text, etype, pos in all_entities
                if (etype, text) not in excluded_set
            ]

        # 执行掩码
        anonymizer.masker.reset()
        anonymized_text, detailed_mapping = anonymizer.masker.mask_all(session['text'], all_entities)

        # 保存脱敏后文本到 session，供后续"继续脱敏"使用
        session['anonymized_text'] = anonymized_text
        session['detailed_mapping'] = detailed_mapping

        # 生成输出文件名
        orig_stem = Path(session['file_name']).stem
        output_name = f"{orig_stem}_anonymized"
        output_path = OUTPUT_DIR / f"{session['id']}_{output_name}"
        input_suffix = Path(session['file_name']).suffix.lower()

        # 归一化 output_format 为 list
        if isinstance(output_format, str):
            formats = [output_format]
        elif isinstance(output_format, (list, tuple)):
            formats = list(output_format) if output_format else ['docx']
        else:
            formats = ['docx']

        saved_files = []
        for fmt in formats:
            files = anonymizer._write_format(
                fmt=fmt,
                input_path=Path(session['file_path']),
                output_path=output_path,
                input_suffix=input_suffix,
                anonymized_content=anonymized_text,
                use_ocr=session.get('use_ocr', False),
                ocr_engine=session.get('ocr_engine', 'rapidocr'),
                whitebox_only=pdf_whitebox,
            )
            saved_files.extend(files)

        # 保存映射表
        mapping_path = OUTPUT_DIR / f"{session['id']}_{output_name}_mapping.json"
        anonymizer.processor.write_mapping(detailed_mapping, str(mapping_path))
        saved_files.append(('mapping_file', str(mapping_path)))

        # 确定主输出文件
        main_output = None
        for key, path in saved_files:
            if key.startswith('output_'):
                main_output = path
                break

        # 收集每种输出格式 → 路径的映射
        output_files = {}
        for key, path in saved_files:
            if key.startswith('output_'):
                fmt_name = key.replace('output_', '')   # docx/pdf/md/txt
                output_files[fmt_name] = path

        session['output_path'] = main_output
        session['output_paths'] = output_files
        session['output_format'] = output_format
        session['mapping_path'] = str(mapping_path)
        session['last_mask_strategy'] = mask_strategy
        session['last_excluded_entities'] = excluded_entities
        session['result'] = {
            'output_path': main_output,
            'output_paths': output_files,
            'mapping_path': str(mapping_path),
            'total_matched': detailed_mapping['metadata']['entity_count'],
            'replacements_made': detailed_mapping['metadata']['replacements_made'],
            'mapping': detailed_mapping['mapping'],
            'saved_files': saved_files,
        }

        return jsonify({
            'status': 'success',
            'output_path': main_output,
            'output_paths': output_files,
            'output_dir': str(OUTPUT_DIR),
            'mapping_path': str(mapping_path),
            'total_matched': detailed_mapping['metadata']['entity_count'],
            'replacements_made': detailed_mapping['metadata']['replacements_made'],
            'mapping': detailed_mapping['mapping'],
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'脱敏失败: {str(e)}'}), 500


@app.route('/api/re-anonymize', methods=['POST'])
def re_anonymize_document():
    """继续脱敏：用户发现残留敏感信息后，添加新实体再次脱敏"""
    data = request.get_json()
    session_id = data.get('session_id')
    new_entities = data.get('entities', [])  # [{"type": "company", "name": "源德盛"}, ...]

    session = sessions.get(session_id)
    if not session:
        return jsonify({'error': '会话不存在或已过期'}), 404

    if not session.get('text'):
        return jsonify({'error': '请先分析并脱敏文档'}), 400

    if not new_entities:
        return jsonify({'error': '请至少添加一个需脱敏的实体'}), 400

    try:
        anonymizer = LegalAnonymizer(
            use_cn_llm=session.get('use_cn_llm', False),
            use_llm=session.get('use_llm', False),
        )

        # 注入用户词典
        user_dict = load_user_dict()
        if user_dict:
            anonymizer.add_custom_entities(user_dict)

        # 恢复之前的自定义实体 + 添加新实体
        all_custom = session.get('custom_entities', []) + new_entities
        session['custom_entities'] = all_custom
        anonymizer.add_custom_entities(all_custom)

        # 获取之前的掩码策略和排除列表
        mask_strategy = session.get('last_mask_strategy', 'placeholder')
        output_format = session.get('output_format', 'docx')
        excluded_entities = session.get('last_excluded_entities', [])

        pdf_whitebox = (mask_strategy == 'whitebox')
        effective_strategy = 'placeholder' if pdf_whitebox else mask_strategy
        if effective_strategy:
            anonymizer.set_all_mask_strategy(effective_strategy)

        # 用原始文本重新检测全部实体
        all_entities = anonymizer._detect_all(session['text'])

        # 过滤排除的
        if excluded_entities:
            excluded_set = {(e['type'], e['name']) for e in excluded_entities}
            all_entities = [
                (text, etype, pos) for text, etype, pos in all_entities
                if (etype, text) not in excluded_set
            ]

        # 重新执行掩码
        anonymizer.masker.reset()
        anonymized_text, detailed_mapping = anonymizer.masker.mask_all(session['text'], all_entities)

        session['anonymized_text'] = anonymized_text
        session['detailed_mapping'] = detailed_mapping

        # 重新写入文件（覆盖之前的输出）
        orig_stem = Path(session['file_name']).stem
        output_name = f"{orig_stem}_anonymized"
        output_path = OUTPUT_DIR / f"{session['id']}_{output_name}"
        input_suffix = Path(session['file_name']).suffix.lower()

        if isinstance(output_format, str):
            formats = [output_format]
        elif isinstance(output_format, (list, tuple)):
            formats = list(output_format) if output_format else ['docx']
        else:
            formats = ['docx']

        saved_files = []
        for fmt in formats:
            files = anonymizer._write_format(
                fmt=fmt,
                input_path=Path(session['file_path']),
                output_path=output_path,
                input_suffix=input_suffix,
                anonymized_content=anonymized_text,
                use_ocr=session.get('use_ocr', False),
                ocr_engine=session.get('ocr_engine', 'rapidocr'),
                whitebox_only=pdf_whitebox,
            )
            saved_files.extend(files)

        # 更新映射表
        mapping_path = OUTPUT_DIR / f"{session['id']}_{output_name}_mapping.json"
        anonymizer.processor.write_mapping(detailed_mapping, str(mapping_path))
        saved_files.append(('mapping_file', str(mapping_path)))

        # 构建 output_paths（每种格式 → 文件路径），前端用来生成多个下载按钮
        output_files = {}
        main_output = None
        for key, path in saved_files:
            if key.startswith('output_'):
                fmt_name = key.replace('output_', '')   # docx / pdf / md / txt
                output_files[fmt_name] = path
                if main_output is None:
                    main_output = path

        session['output_path'] = main_output
        session['output_paths'] = output_files
        session['mapping_path'] = str(mapping_path)
        session['result'] = {
            'output_path': main_output,
            'output_paths': output_files,
            'mapping_path': str(mapping_path),
            'total_matched': detailed_mapping['metadata']['entity_count'],
            'replacements_made': detailed_mapping['metadata']['replacements_made'],
            'mapping': detailed_mapping['mapping'],
            'saved_files': saved_files,
        }

        return jsonify({
            'status': 'success',
            'output_path': main_output,
            'output_paths': output_files,
            'mapping_path': str(mapping_path),
            'total_matched': detailed_mapping['metadata']['entity_count'],
            'replacements_made': detailed_mapping['metadata']['replacements_made'],
            'mapping': detailed_mapping['mapping'],
            'new_entities_added': len(new_entities),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'继续脱敏失败: {str(e)}'}), 500


def _anonymize_filename(session: dict) -> str:
    """对文件名中的敏感信息也做脱敏替换"""
    orig_stem = Path(session['file_name']).stem
    mapping = session.get('detailed_mapping', {}).get('mapping', {})
    if not mapping:
        return orig_stem

    # 构建替换表：原始值 -> 占位符，按长度降序
    replacements = {}
    for placeholder, info in mapping.items():
        original = info.get('original', '')
        if original and len(original) >= 2:
            replacements[original] = placeholder
    sorted_originals = sorted(replacements.keys(), key=len, reverse=True)

    result = orig_stem
    for original in sorted_originals:
        result = result.replace(original, replacements[original])
    return result


@app.route('/api/download/<session_id>', methods=['GET'])
def download_file(session_id):
    """下载脱敏后的文件。可选 ?fmt=docx/pdf/md/txt 指定格式。"""
    session = sessions.get(session_id)
    if not session:
        return jsonify({'error': '文件不存在'}), 404

    fmt = request.args.get('fmt', '').lower()
    target_path = None
    if fmt and session.get('output_paths'):
        target_path = session['output_paths'].get(fmt)
    if not target_path:
        target_path = session.get('output_path')
    if not target_path:
        return jsonify({'error': '文件不存在'}), 404

    output_path = Path(target_path)
    if not output_path.exists():
        return jsonify({'error': '输出文件不存在'}), 404

    # 构造下载文件名（文件名也脱敏）
    anonymized_stem = _anonymize_filename(session)
    download_name = f"{anonymized_stem}_脱敏版{output_path.suffix}"

    return send_file(
        str(output_path),
        as_attachment=True,
        download_name=download_name,
    )


@app.route('/api/download-mapping/<session_id>', methods=['GET'])
def download_mapping(session_id):
    """下载映射表"""
    session = sessions.get(session_id)
    if not session or not session.get('mapping_path'):
        return jsonify({'error': '映射表不存在'}), 404

    mapping_path = Path(session['mapping_path'])
    if not mapping_path.exists():
        return jsonify({'error': '映射表文件不存在'}), 404

    anonymized_stem = _anonymize_filename(session)
    download_name = f"{anonymized_stem}_映射表.json"

    return send_file(
        str(mapping_path),
        as_attachment=True,
        download_name=download_name,
    )


@app.route('/api/user-dict', methods=['GET'])
def get_user_dict():
    """获取用户词典"""
    entries = load_user_dict()
    return jsonify({'entries': entries, 'count': len(entries)})


@app.route('/api/user-dict/add', methods=['POST'])
def add_user_dict():
    """向用户词典添加词条"""
    data = request.get_json()
    new_entries = data.get('entries', [])
    current = load_user_dict()
    added = 0
    for e in new_entries:
        if e.get('name') and not any(x['type'] == e['type'] and x['name'] == e['name'] for x in current):
            current.append({'type': e['type'], 'name': e['name']})
            added += 1
    save_user_dict(current)
    return jsonify({'entries': current, 'count': len(current), 'added': added})


@app.route('/api/user-dict/remove', methods=['POST'])
def remove_user_dict():
    """从用户词典删除词条"""
    data = request.get_json()
    to_remove = data.get('entries', [])
    current = load_user_dict()
    current = [x for x in current
               if not any(e['type'] == x['type'] and e['name'] == x['name'] for e in to_remove)]
    save_user_dict(current)
    return jsonify({'entries': current, 'count': len(current)})


@app.route('/api/user-dict/clear', methods=['POST'])
def clear_user_dict():
    """清空用户词典"""
    save_user_dict([])
    return jsonify({'entries': [], 'count': 0})


# ==================== 批量处理 ====================

# 批次状态：batch_id -> {created_at, items: [...], done, total}
batches: Dict[str, dict] = {}
BATCH_TIMEOUT = 7200  # 2 小时


def _cleanup_batches():
    now = time.time()
    expired = [bid for bid, b in batches.items() if now - b['created_at'] > BATCH_TIMEOUT]
    for bid in expired:
        # 不再清理输出文件，让用户来得及取回
        del batches[bid]


def _estimate_eta(file_path: str, is_scanned: bool) -> float:
    """根据文件类型/大小预估处理秒数（保守估计）"""
    suffix = Path(file_path).suffix.lower()
    size_kb = os.path.getsize(file_path) / 1024
    if suffix == '.pdf':
        # 用页数判断更准；扫描版 OCR 慢约 12-15s/页，文字版 PDF 约 0.5-1s/页
        try:
            import fitz
            pages = len(fitz.open(file_path))
        except Exception:
            pages = max(1, int(size_kb / 80))
        if is_scanned:
            return max(8.0, pages * 13.0 + 3.0)
        return max(2.0, pages * 0.8 + 1.5)
    if suffix in ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp'):
        return 8.0
    if suffix in ('.docx', '.doc'):
        return max(2.0, size_kb / 100)
    return max(1.0, size_kb / 200)


def _process_batch_item(batch_id: str, item: dict, options: dict):
    """单个文件脱敏（在后台线程里跑）"""
    try:
        item['status'] = 'processing'
        item['stage'] = 'detect'
        item['started_at'] = time.time()

        anonymizer = LegalAnonymizer(
            use_cn_llm=options.get('use_cn_llm', False),
            use_llm=options.get('use_llm', False),
        )
        # whitebox 模式仍然用 placeholder 策略生成文本占位符（[PERSON_1]等），
        # 但会传 pdf_whitebox=True 让 PDF 输出层不画文字、只留白框
        strategy = options.get('mask_strategy', 'placeholder')
        pdf_whitebox = (strategy == 'whitebox')
        anonymizer.set_all_mask_strategy('placeholder' if pdf_whitebox else strategy)
        anonymizer.set_placeholder_style(options.get('placeholder_style', 'english_bracket'))

        # 注入用户词典
        ud = load_user_dict()
        if ud:
            anonymizer.add_custom_entities(ud)

        input_path = Path(item['file_path'])
        # input_path.stem 已经带了 batch_<id>_NN_ 前缀（来自 upload 时的 safe_name），
        # 这里取原始文件名的 stem 避免重复前缀
        orig_stem = Path(item['name']).stem
        output_stem = OUTPUT_DIR / f"batch_{batch_id}_{item['idx']:02d}_{orig_stem}"

        item['stage'] = 'anonymize'
        formats = options.get('output_formats') or ['pdf' if input_path.suffix.lower() == '.pdf' else 'docx']
        is_scanned = is_scanned_pdf(str(input_path)) if input_path.suffix.lower() == '.pdf' else False
        item['is_scanned'] = is_scanned
        item['eta_s'] = round(_estimate_eta(str(input_path), is_scanned), 1)

        result = anonymizer.anonymize_file(
            input_path=str(input_path),
            output_path=str(output_stem),
            output_format=formats,
            use_ocr=is_scanned,
            ocr_engine=options.get('ocr_engine', 'rapidocr'),
            save_text_backup=True,
            save_mapping=True,
            pdf_whitebox=pdf_whitebox,
        )
        if 'error' in result:
            item['status'] = 'error'
            item['error'] = result['error']
            return

        info = result.get('result', {})
        # 收集所有输出文件（output_pdf / output_docx / mapping_file / text_backup）
        outputs = {}
        for k, v in info.items():
            if k in ('output_pdf', 'output_docx', 'output_md', 'output_txt', 'mapping_file', 'text_backup'):
                outputs[k] = v
        item['outputs'] = outputs
        item['total_matched'] = info.get('total_matched', 0)
        item['replacements_made'] = info.get('replacements_made', 0)
        item['is_scanned'] = is_scanned
        item['status'] = 'done'
        item['stage'] = 'completed'
    except Exception as e:
        import traceback
        traceback.print_exc()
        item['status'] = 'error'
        item['error'] = str(e)
    finally:
        # 记录完成时间和实际耗时
        if 'started_at' in item:
            item['finished_at'] = time.time()
            item['elapsed_s'] = round(item['finished_at'] - item['started_at'], 1)
        batch = batches.get(batch_id)
        if batch:
            batch['done'] = sum(1 for it in batch['items'] if it['status'] in ('done', 'error'))


@app.route('/api/restore', methods=['POST'])
def restore_text():
    """根据脱敏映射 JSON 把脱敏文本还原成原文"""
    data = request.get_json() or {}
    anonymized_text = data.get('text', '')
    mapping_data = data.get('mapping')

    if not anonymized_text:
        return jsonify({'error': '请粘贴脱敏后的文本'}), 400
    if not mapping_data:
        return jsonify({'error': '请提供映射字典（mapping.json 的内容或上传文件）'}), 400

    # mapping 可能是直接的 {占位符: {original, type}}，
    # 也可能是工具导出的完整 JSON：{metadata, mapping, replacement_log}
    if isinstance(mapping_data, dict) and 'mapping' in mapping_data and isinstance(mapping_data['mapping'], dict):
        mapping_dict = mapping_data['mapping']
    else:
        mapping_dict = mapping_data

    try:
        restored = LegalAnonymizer.restore_text(anonymized_text, mapping_dict)
        return jsonify({
            'restored': restored,
            'replacements': len(mapping_dict) if isinstance(mapping_dict, dict) else 0,
        })
    except Exception as e:
        return jsonify({'error': f'还原失败: {str(e)}'}), 500


@app.route('/api/batch/upload', methods=['POST'])
def batch_upload():
    """批量上传文件，返回 batch_id 与每个文件的元信息"""
    _cleanup_batches()
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': '未选择文件'}), 400

    batch_id = uuid.uuid4().hex[:10]
    items = []
    for idx, f in enumerate(files, 1):
        if not f.filename:
            continue
        suffix = Path(f.filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            items.append({
                'idx': idx, 'name': f.filename, 'size': 0,
                'status': 'rejected', 'error': f'不支持的格式 {suffix}',
                'file_path': None, 'outputs': {},
            })
            continue
        safe_name = f"batch_{batch_id}_{idx:02d}_{f.filename}"
        save_path = UPLOAD_DIR / safe_name
        f.save(str(save_path))
        items.append({
            'idx': idx,
            'name': f.filename,
            'file_path': str(save_path),
            'size': os.path.getsize(save_path),
            'status': 'pending',
            'stage': '',
            'is_scanned': False,
            'outputs': {},
            'total_matched': 0,
            'replacements_made': 0,
            'error': None,
        })

    batches[batch_id] = {
        'id': batch_id,
        'created_at': time.time(),
        'items': items,
        'total': sum(1 for it in items if it['status'] == 'pending'),
        'done': 0,
        'started': False,
    }
    return jsonify({
        'batch_id': batch_id,
        'count': len(items),
        'items': [
            {'idx': it['idx'], 'name': it['name'], 'size': it['size'],
             'status': it['status'], 'error': it.get('error')}
            for it in items
        ],
    })


@app.route('/api/batch/start', methods=['POST'])
def batch_start():
    """开始批量脱敏（异步，逐个跑）"""
    data = request.get_json() or {}
    batch_id = data.get('batch_id')
    options = {
        'mask_strategy': data.get('mask_strategy', 'placeholder'),
        'placeholder_style': data.get('placeholder_style', 'english_bracket'),
        'output_formats': data.get('output_formats') or None,
        'use_cn_llm': bool(data.get('use_cn_llm', False)),
        'use_llm': bool(data.get('use_llm', False)),
        'ocr_engine': data.get('ocr_engine', 'rapidocr'),
    }
    batch = batches.get(batch_id)
    if not batch:
        return jsonify({'error': '批次不存在或已过期'}), 404
    if batch['started']:
        return jsonify({'error': '批次已开始'}), 400

    batch['started'] = True

    def _run():
        for it in batch['items']:
            if it['status'] == 'pending':
                _process_batch_item(batch_id, it, options)

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started', 'batch_id': batch_id, 'total': batch['total']})


@app.route('/api/batch/status/<batch_id>', methods=['GET'])
def batch_status(batch_id):
    batch = batches.get(batch_id)
    if not batch:
        return jsonify({'error': '批次不存在或已过期'}), 404
    return jsonify({
        'batch_id': batch_id,
        'total': batch['total'],
        'done': batch['done'],
        'progress': round(batch['done'] / batch['total'] * 100, 1) if batch['total'] else 0,
        'all_finished': batch['done'] >= batch['total'],
        'items': [
            {
                'idx': it['idx'], 'name': it['name'], 'status': it['status'],
                'stage': it.get('stage', ''),
                'error': it.get('error'),
                'is_scanned': it.get('is_scanned', False),
                'total_matched': it.get('total_matched', 0),
                'replacements_made': it.get('replacements_made', 0),
                'outputs': it.get('outputs', {}),
                'eta_s': it.get('eta_s', 0),
                'started_at': it.get('started_at', 0),
                'finished_at': it.get('finished_at', 0),
                'elapsed_s': it.get('elapsed_s', 0),
            }
            for it in batch['items']
        ],
        'now': time.time(),
    })


@app.route('/api/batch/download/<batch_id>', methods=['GET'])
def batch_download(batch_id):
    """打包下载整个批次的所有输出文件为 zip"""
    import zipfile, io
    from urllib.parse import quote
    batch = batches.get(batch_id)
    if not batch:
        return jsonify({'error': '批次不存在或已过期'}), 404

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for it in batch['items']:
            if it['status'] != 'done':
                continue
            # 在 zip 内的目录结构：原文件名（去后缀）/ {输出文件名}
            stem = Path(it['name']).stem
            # 输出文件实际名带 batch_ 前缀，重命名为简洁的：原名{.pdf|_mapping.json|.txt}
            for kind, path in (it.get('outputs') or {}).items():
                if not path or not Path(path).exists():
                    continue
                p = Path(path)
                # 把 batch_<id>_NN_ 前缀剥掉，让 zip 里文件名干净
                clean_name = re.sub(r'^batch_[a-f0-9]+_\d+_', '', p.name)
                arc_name = f"{stem}/{clean_name}"
                zf.write(str(p), arc_name)
    buf.seek(0)

    # Content-Disposition：filename 用 ASCII，filename* 用 UTF-8 编码（RFC 5987），
    # 否则 Werkzeug 会因非 Latin-1 字符报 UnicodeError 让请求挂死。
    ascii_name = f'batch_{batch_id}_results.zip'
    utf8_name = quote(f'批量脱敏结果_{batch_id}.zip', safe='')
    from flask import Response
    return Response(
        buf.getvalue(),
        mimetype='application/zip',
        headers={
            'Content-Disposition': (
                f"attachment; filename=\"{ascii_name}\"; "
                f"filename*=UTF-8''{utf8_name}"
            ),
        },
    )


def find_free_port(start=8080, end=8099):
    """找到一个可用端口"""
    import socket
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return start


def cleanup_old_files():
    """启动时清理超过24小时的临时上传文件，超过48小时的输出文件"""
    now = time.time()
    for directory, max_age in [(UPLOAD_DIR, 86400), (OUTPUT_DIR, 172800)]:
        for f in directory.iterdir():
            if f.is_file() and (now - f.stat().st_mtime) > max_age:
                try:
                    f.unlink()
                except Exception:
                    pass


import atexit

@atexit.register
def on_exit():
    """服务停止时清理所有上传临时文件（输出文件保留供用户取回）"""
    for f in UPLOAD_DIR.iterdir():
        if f.is_file():
            try:
                f.unlink()
            except Exception:
                pass


if __name__ == '__main__':
    import threading
    import webbrowser

    cleanup_old_files()
    port = find_free_port()

    print()
    print("=" * 50)
    print("  法律文档脱敏工具 - Web 界面")
    print("  by 黄灵宝同学")
    print("=" * 50)
    print()
    print(f"  Inbox 文件夹: {INBOX_DIR}")
    print(f"  输出文件夹:   {OUTPUT_DIR}")
    print()
    print(f"  请在浏览器中打开: http://127.0.0.1:{port}")
    print()
    print("  数据完全本地处理，不上传云端")
    print("  按 Ctrl+C 停止服务")
    print("=" * 50)
    print()

    # 延迟 1.5 秒后自动打开浏览器
    threading.Timer(3.0, lambda: webbrowser.open(f'http://127.0.0.1:{port}')).start()

    app.run(host='127.0.0.1', port=port, debug=False)
