from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import traceback

from garminconnect import Garmin


SERVER_NAME = "garmin-mcp-cn-vercel"


def json_response(handler, status_code, data):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def text_tool_result(text):
    return {
        "content": [
            {
                "type": "text",
                "text": text,
            }
        ]
    }


def get_garmin_client():
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    is_cn = os.environ.get("GARMIN_IS_CN", "false").lower() == "true"

    if not email or not password:
        raise RuntimeError("缺少 GARMIN_EMAIL 或 GARMIN_PASSWORD 环境变量")

    client = Garmin(email, password, is_cn=is_cn)
    client.login()
    return client


def list_tools():
    return [
        {
            "name": "get_recent_activities",
            "description": "获取 Garmin 最近运动记录，支持佳明中国区。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回几条运动记录，默认 10 条",
                        "default": 10
                    }
                }
            }
        },
        {
            "name": "get_activity_detail",
            "description": "根据 activity_id 获取某次运动详情。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "integer",
                        "description": "Garmin 活动 ID"
                    }
                },
                "required": ["activity_id"]
            }
        }
    ]


def call_tool(name, arguments):
    client = get_garmin_client()

    if name == "get_recent_activities":
        limit = int(arguments.get("limit", 10))
        activities = client.get_activities(0, limit)
        return text_tool_result(json.dumps(activities, ensure_ascii=False, indent=2))

    if name == "get_activity_detail":
        activity_id = int(arguments["activity_id"])
        detail = client.get_activity(activity_id)
        return text_tool_result(json.dumps(detail, ensure_ascii=False, indent=2))

    raise RuntimeError(f"未知工具：{name}")


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            token = query.get("token", [""])[0]
            expected_token = os.environ.get("MCP_AUTH_TOKEN")

            if not expected_token or token != expected_token:
                json_response(self, 401, {
                    "error": "Unauthorized"
                })
                return

            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8")
            request = json.loads(raw_body) if raw_body else {}

            method = request.get("method")
            request_id = request.get("id")
            params = request.get("params") or {}

            if method == "notifications/initialized":
                self.send_response(204)
                self.end_headers()
                return

            if method == "initialize":
                json_response(self, 200, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": SERVER_NAME,
                            "version": "0.1.0"
                        }
                    }
                })
                return

            if method == "tools/list":
                json_response(self, 200, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": list_tools()
                    }
                })
                return

            if method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments") or {}
                result = call_tool(tool_name, arguments)

                json_response(self, 200, {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                })
                return

            json_response(self, 400, {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Unsupported method: {method}"
                }
            })

        except Exception as e:
            json_response(self, 500, {
                "error": str(e),
                "traceback": traceback.format_exc()
            })
