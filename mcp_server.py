#!/usr/bin/env python3
"""
Legal Document Anonymizer - MCP Server
法律文档脱敏工具 - MCP Server

通过 MCP (Model Context Protocol) 协议提供脱敏服务。
数据完全本地处理，不上传云端。

配置方法 - 在 ~/.claude/settings.json 中添加:
{
  "mcpServers": {
    "legal-anonymizer": {
      "command": "python3",
      "args": ["/Users/rainbow/AIwork/legal-anonymizer/mcp_server.py"]
    }
  }
}
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Any

# 确保模块路径
sys.path.insert(0, str(Path(__file__).parent))

from anonymizer import LegalAnonymizer

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


def create_mcp_server():
    """创建 MCP Server"""
    if not HAS_MCP:
        raise ImportError("需要安装 MCP SDK: pip install mcp")

    server = Server("legal-anonymizer-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="anonymize_file",
                description="脱敏文件 - 支持 PDF、Word(.doc/.docx)、图片、文本。自动识别人名、公司名、身份证、手机号等敏感信息。数据完全本地处理。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "input_path": {
                            "type": "string",
                            "description": "输入文件路径"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "输出文件路径（可选，默认在同目录生成）"
                        },
                        "entities": {
                            "type": "string",
                            "description": "自定义实体 JSON 字符串，格式: [{\"type\":\"person\",\"name\":\"张三\"}]（可选）"
                        },
                        "entities_path": {
                            "type": "string",
                            "description": "自定义实体 JSON 文件路径（可选）"
                        },
                        "output_format": {
                            "type": "string",
                            "description": "输出格式",
                            "enum": ["auto", "txt", "pdf", "docx", "md"],
                            "default": "auto"
                        },
                        "only_types": {
                            "type": "string",
                            "description": "只脱敏指定类型，逗号分隔（可选）"
                        },
                        "exclude_types": {
                            "type": "string",
                            "description": "排除指定类型，逗号分隔（可选）"
                        },
                        "mask_strategy": {
                            "type": "string",
                            "description": "掩码策略: placeholder（占位符）或 partial（部分掩码）",
                            "enum": ["placeholder", "partial"],
                            "default": "placeholder"
                        },
                        "use_ocr": {
                            "type": "boolean",
                            "description": "对PDF使用OCR（处理扫描版）",
                            "default": False
                        }
                    },
                    "required": ["input_path"]
                }
            ),
            Tool(
                name="anonymize_text",
                description="脱敏文本内容 - 直接对文本进行脱敏处理，自动识别敏感信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "要脱敏的文本内容"
                        },
                        "entities": {
                            "type": "string",
                            "description": "自定义实体 JSON 字符串（可选）"
                        },
                        "only_types": {
                            "type": "string",
                            "description": "只脱敏指定类型，逗号分隔（可选）"
                        },
                        "exclude_types": {
                            "type": "string",
                            "description": "排除指定类型，逗号分隔（可选）"
                        },
                        "mask_strategy": {
                            "type": "string",
                            "description": "掩码策略",
                            "enum": ["placeholder", "partial"]
                        }
                    },
                    "required": ["text"]
                }
            ),
            Tool(
                name="analyze_document",
                description="分析文档敏感信息 - 识别文档中的敏感信息但不实际脱敏",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "input_path": {
                            "type": "string",
                            "description": "输入文件路径"
                        },
                        "only_types": {
                            "type": "string",
                            "description": "只分析指定类型，逗号分隔（可选）"
                        },
                        "exclude_types": {
                            "type": "string",
                            "description": "排除指定类型，逗号分隔（可选）"
                        }
                    },
                    "required": ["input_path"]
                }
            ),
            Tool(
                name="list_supported_types",
                description="列出所有支持的敏感信息类型",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Any) -> list[TextContent]:
        # 每次调用创建新实例，避免状态污染
        anonymizer = LegalAnonymizer()

        try:
            if name == "anonymize_file":
                return await _handle_anonymize_file(anonymizer, arguments)
            elif name == "anonymize_text":
                return await _handle_anonymize_text(anonymizer, arguments)
            elif name == "analyze_document":
                return await _handle_analyze_document(anonymizer, arguments)
            elif name == "list_supported_types":
                return await _handle_list_types(anonymizer)
            else:
                return [TextContent(type="text", text=json.dumps(
                    {"error": f"未知工具: {name}"}, ensure_ascii=False
                ))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps(
                {"error": str(e)}, ensure_ascii=False
            ))]

    async def _handle_anonymize_file(anonymizer: LegalAnonymizer, args: dict) -> list[TextContent]:
        input_path = args["input_path"]
        output_path = args.get("output_path")
        output_format = args.get("output_format", "auto")
        use_ocr = args.get("use_ocr", False)

        # 加载自定义实体
        custom_entities = _parse_entities(args)

        # 解析字段过滤
        only_types = args.get("only_types", "").split(",") if args.get("only_types") else None
        exclude_types = args.get("exclude_types", "").split(",") if args.get("exclude_types") else None

        # 设置掩码策略
        if args.get("mask_strategy"):
            anonymizer.set_all_mask_strategy(args["mask_strategy"])

        result = anonymizer.anonymize_file(
            input_path, output_path,
            custom_entities=custom_entities,
            output_format=output_format,
            only_types=only_types,
            exclude_types=exclude_types,
            use_ocr=use_ocr
        )

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    async def _handle_anonymize_text(anonymizer: LegalAnonymizer, args: dict) -> list[TextContent]:
        text = args["text"]

        custom_entities = _parse_entities(args)
        if custom_entities:
            anonymizer.add_custom_entities(custom_entities)

        only_types = args.get("only_types", "").split(",") if args.get("only_types") else None
        exclude_types = args.get("exclude_types", "").split(",") if args.get("exclude_types") else None

        if args.get("mask_strategy"):
            anonymizer.set_all_mask_strategy(args["mask_strategy"])

        anonymized_text, mapping = anonymizer.anonymize_text(text, only_types, exclude_types)

        result = {
            "action": "anonymize_text",
            "status": "success",
            "result": {
                "anonymized_text": anonymized_text,
                "mapping": mapping["mapping"],
                "total_matched": mapping["metadata"]["entity_count"],
                "replacements_made": mapping["metadata"]["replacements_made"],
            }
        }

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    async def _handle_analyze_document(anonymizer: LegalAnonymizer, args: dict) -> list[TextContent]:
        input_path = args["input_path"]

        only_types = args.get("only_types", "").split(",") if args.get("only_types") else None
        exclude_types = args.get("exclude_types", "").split(",") if args.get("exclude_types") else None

        result = anonymizer.analyze_file(input_path, only_types, exclude_types)

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    async def _handle_list_types(anonymizer: LegalAnonymizer) -> list[TextContent]:
        types = anonymizer.get_supported_types()

        # 补充自动检测支持的类型
        auto_types = {
            'person': '人名（自动检测）',
            'company': '公司名（自动检测）',
            'law_firm': '律师事务所（自动检测）',
            'court': '法院名称（自动检测）',
            'government': '政府机关（自动检测）',
            'institution': '机构名称（自动检测）',
            'bank_name': '银行名称（自动检测）',
        }
        types.update(auto_types)

        result = {
            "action": "list_supported_types",
            "status": "success",
            "result": {
                "types": types,
                "count": len(types)
            }
        }

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    def _parse_entities(args: dict):
        """解析自定义实体参数"""
        entities_str = args.get("entities")
        entities_path = args.get("entities_path")

        if entities_path:
            path = Path(entities_path)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        elif entities_str:
            return json.loads(entities_str)

        return None

    return server


async def main():
    server = create_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    if not HAS_MCP:
        print("错误: 需要安装 MCP SDK", file=sys.stderr)
        print("安装命令: pip install mcp", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main())
