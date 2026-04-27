from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import json
import os
import traceback

from garminconnect import Garmin


app = FastAPI()
SERVER_NAME = "garmin-mcp-cn-vercel"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
}


def text_tool_result(text: str):
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
            "description": "根据 activity_id 获取某次 Garmin 运动详情。",
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


def call_tool(name: str, arguments: dict):
    client = get_garmin_client()

    if name == "get_recent_activities":
        limit = int(arguments.get("limit", 10))
        activities = client.get_activities(0, limit)
        return text_tool_result(json.dumps(activities, ensure_ascii=False, indent=2, default=str))

    if name == "get_activity_detail":
        activity_id = int(arguments["activity_id"])
        detail = client.get_activity(activity_id)
        return text_tool_result(json.dumps(detail, ensure_ascii=False, indent=2, default=str))

    raise RuntimeError(f"未知工具：{name}")


def handle_rpc(request_data: dict):
    method = request_data.get("method")
    request_id = request_data.get("id")
    params = request_data.get("params") or {}

    if method == "initialize":
        return {
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
        }

    if method == "notifications/initialized":
        return None

    if method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {}
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": list_tools()
            }
        }

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        result = call_tool(tool_name, arguments)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601,
            "message": f"Unsupported method: {method}"
        }
    }


@app.options("/api/mcp")
async def options_mcp():
    return Response(status_code=204, headers=CORS_HEADERS)


@app.post("/api/mcp")
async def mcp_endpoint(request: Request):
    try:
        token = request.query_params.get("token", "")
        expected_token = os.environ.get("MCP_AUTH_TOKEN")

        if not expected_token or token != expected_token:
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized"},
                headers=CORS_HEADERS
            )

        request_data = await request.json()

        if isinstance(request_data, list):
            results = []
            for item in request_data:
                result = handle_rpc(item)
                if result is not None:
                    results.append(result)

            if not results:
                return Response(status_code=204, headers=CORS_HEADERS)

            return JSONResponse(
                status_code=200,
                content=results,
                headers=CORS_HEADERS
            )

        result = handle_rpc(request_data)

        if result is None:
            return Response(status_code=204, headers=CORS_HEADERS)

        return JSONResponse(
            status_code=200,
            content=result,
            headers=CORS_HEADERS
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            },
            headers=CORS_HEADERS
        )


@app.get("/")
async def home():
    return {
        "status": "ok",
        "name": SERVER_NAME,
        "message": "Garmin CN MCP server is running"
    }