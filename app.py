from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import json
import os
import traceback
from datetime import date as date_class

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


def json_text(data):
    return text_tool_result(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def get_garmin_client():
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    is_cn = os.environ.get("GARMIN_IS_CN", "false").lower() == "true"

    if not email or not password:
        raise RuntimeError("缺少 GARMIN_EMAIL 或 GARMIN_PASSWORD 环境变量")

    client = Garmin(email, password, is_cn=is_cn)
    client.login()
    return client


def today_string():
    return date_class.today().isoformat()


def call_first_available(client, method_names, *args):
    """
    尝试调用多个可能的方法名。
    这样做是为了兼容 garminconnect 不同版本中方法名略有差异的情况。
    """
    errors = []

    for method_name in method_names:
        method = getattr(client, method_name, None)

        if method is None:
            errors.append(f"{method_name}: method_not_found")
            continue

        try:
            return {
                "ok": True,
                "method": method_name,
                "data": method(*args),
            }
        except TypeError as e:
            errors.append(f"{method_name}: TypeError: {str(e)}")
        except Exception as e:
            errors.append(f"{method_name}: {type(e).__name__}: {str(e)}")

    return {
        "ok": False,
        "methods_tried": method_names,
        "errors": errors,
        "data": None,
    }


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
        },
        {
            "name": "get_daily_health_summary",
            "description": "获取某一天的综合健康数据，包括睡眠、HRV、静息心率、Body Battery、压力、呼吸、血氧、训练准备度、训练状态等。日期格式 YYYY-MM-DD。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期，格式 YYYY-MM-DD。例如 2026-04-27。不传则默认今天。"
                    }
                }
            }
        },
        {
            "name": "get_sleep_data",
            "description": "获取某一天的睡眠数据。日期格式 YYYY-MM-DD。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期，格式 YYYY-MM-DD。不传则默认今天。"
                    }
                }
            }
        },
        {
            "name": "get_hrv_data",
            "description": "获取某一天的 HRV 数据。日期格式 YYYY-MM-DD。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期，格式 YYYY-MM-DD。不传则默认今天。"
                    }
                }
            }
        },
        {
            "name": "get_resting_heart_rate",
            "description": "获取某一天的静息心率数据。日期格式 YYYY-MM-DD。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期，格式 YYYY-MM-DD。不传则默认今天。"
                    }
                }
            }
        },
        {
            "name": "get_body_battery",
            "description": "获取某一天的 Body Battery 数据。日期格式 YYYY-MM-DD。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期，格式 YYYY-MM-DD。不传则默认今天。"
                    }
                }
            }
        },
        {
            "name": "get_stress_data",
            "description": "获取某一天的压力数据。日期格式 YYYY-MM-DD。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期，格式 YYYY-MM-DD。不传则默认今天。"
                    }
                }
            }
        },
        {
            "name": "get_respiration_data",
            "description": "获取某一天的呼吸率数据。日期格式 YYYY-MM-DD。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期，格式 YYYY-MM-DD。不传则默认今天。"
                    }
                }
            }
        },
        {
            "name": "get_spo2_data",
            "description": "获取某一天的血氧数据。日期格式 YYYY-MM-DD。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期，格式 YYYY-MM-DD。不传则默认今天。"
                    }
                }
            }
        },
        {
            "name": "get_training_readiness",
            "description": "获取某一天的训练准备度数据。日期格式 YYYY-MM-DD。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "日期，格式 YYYY-MM-DD。不传则默认今天。"
                    }
                }
            }
        },
        {
            "name": "get_training_status",
            "description": "获取当前训练状态数据。",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "get_workouts_or_training_plan",
            "description": "尝试获取 Garmin 训练计划 / workouts 数据。不同账号和 Garmin API 权限下返回内容可能不同。",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
    ]


def call_tool(name: str, arguments: dict):
    client = get_garmin_client()

    if name == "get_recent_activities":
        limit = int(arguments.get("limit", 10))
        activities = client.get_activities(0, limit)
        return json_text(activities)

    if name == "get_activity_detail":
        activity_id = int(arguments["activity_id"])
        detail = client.get_activity(activity_id)
        return json_text(detail)

    if name == "get_sleep_data":
        target_date = arguments.get("date") or today_string()
        result = call_first_available(
            client,
            ["get_sleep_data", "get_sleep"],
            target_date
        )
        return json_text({"date": target_date, "sleep": result})

    if name == "get_hrv_data":
        target_date = arguments.get("date") or today_string()
        result = call_first_available(
            client,
            ["get_hrv_data", "get_hrv"],
            target_date
        )
        return json_text({"date": target_date, "hrv": result})

    if name == "get_resting_heart_rate":
        target_date = arguments.get("date") or today_string()
        result = call_first_available(
            client,
            ["get_rhr_day", "get_resting_heart_rate", "get_resting_hr"],
            target_date
        )
        return json_text({"date": target_date, "resting_heart_rate": result})

    if name == "get_body_battery":
        target_date = arguments.get("date") or today_string()
        result = call_first_available(
            client,
            ["get_body_battery", "get_body_battery_events"],
            target_date
        )
        return json_text({"date": target_date, "body_battery": result})

    if name == "get_stress_data":
        target_date = arguments.get("date") or today_string()
        result = call_first_available(
            client,
            ["get_stress_data", "get_stress"],
            target_date
        )
        return json_text({"date": target_date, "stress": result})

    if name == "get_respiration_data":
        target_date = arguments.get("date") or today_string()
        result = call_first_available(
            client,
            ["get_respiration_data", "get_respiration"],
            target_date
        )
        return json_text({"date": target_date, "respiration": result})

    if name == "get_spo2_data":
        target_date = arguments.get("date") or today_string()
        result = call_first_available(
            client,
            ["get_spo2_data", "get_spo2"],
            target_date
        )
        return json_text({"date": target_date, "spo2": result})

    if name == "get_training_readiness":
        target_date = arguments.get("date") or today_string()
        result = call_first_available(
            client,
            ["get_training_readiness", "get_training_readiness_data"],
            target_date
        )
        return json_text({"date": target_date, "training_readiness": result})

    if name == "get_training_status":
        result = call_first_available(
            client,
            ["get_training_status", "get_training_status_data"]
        )
        return json_text({"training_status": result})

    if name == "get_workouts_or_training_plan":
        result = call_first_available(
            client,
            [
                "get_workouts",
                "get_workout_schedule",
                "get_training_plan",
                "get_training_plans"
            ]
        )
        return json_text({"workouts_or_training_plan": result})

    if name == "get_daily_health_summary":
        target_date = arguments.get("date") or today_string()

        summary = {
            "date": target_date,
            "sleep": call_first_available(
                client,
                ["get_sleep_data", "get_sleep"],
                target_date
            ),
            "hrv": call_first_available(
                client,
                ["get_hrv_data", "get_hrv"],
                target_date
            ),
            "resting_heart_rate": call_first_available(
                client,
                ["get_rhr_day", "get_resting_heart_rate", "get_resting_hr"],
                target_date
            ),
            "body_battery": call_first_available(
                client,
                ["get_body_battery", "get_body_battery_events"],
                target_date
            ),
            "stress": call_first_available(
                client,
                ["get_stress_data", "get_stress"],
                target_date
            ),
            "respiration": call_first_available(
                client,
                ["get_respiration_data", "get_respiration"],
                target_date
            ),
            "spo2": call_first_available(
                client,
                ["get_spo2_data", "get_spo2"],
                target_date
            ),
            "training_readiness": call_first_available(
                client,
                ["get_training_readiness", "get_training_readiness_data"],
                target_date
            ),
            "training_status": call_first_available(
                client,
                ["get_training_status", "get_training_status_data"]
            )
        }

        return json_text(summary)

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
                    "version": "0.2.0"
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
        "version": "0.2.0",
        "message": "Garmin CN MCP server is running"
    }
