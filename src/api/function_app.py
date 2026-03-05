import azure.functions as func
import json
import os
from pathlib import Path
from typing import Any

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _get_sample_record_count(schema: dict[str, Any]) -> int:
    sample_data_size = schema.get("sample_data_size")
    if isinstance(sample_data_size, int):
        return sample_data_size

    sample_data_config = schema.get("sample_data_config")
    if not isinstance(sample_data_config, dict):
        sample_data_config_typed: dict[str, Any] = {}
    else:
        sample_data_config_typed = sample_data_config  # type: ignore[assignment]

    record_count = sample_data_config_typed.get("record_count")
    if isinstance(record_count, int):
        return record_count

    return 100_000


@app.route(route="industries", methods=["GET"])
def get_industries(req: func.HttpRequest) -> func.HttpResponse:
    """Return list of available industry templates"""
    
    industries: list[dict[str, Any]] = []
    templates_dir = Path(__file__).parent.parent.parent / "industry-templates"
    
    if templates_dir.exists():
        for industry_dir in templates_dir.iterdir():
            if industry_dir.is_dir():
                schema_file = industry_dir / "schema.json"
                if schema_file.exists():
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema = json.load(f)
                        industries.append({
                            "industry": schema["industry"],
                            "display_name": schema["display_name"],
                            "description": schema["description"],
                            "icon": schema["icon"],
                            "sample_data_size": _get_sample_record_count(schema)
                        })
    else:
        # Fallback if templates not found
        industries = [
            {
                "industry": "healthcare",
                "display_name": "Healthcare",
                "description": "Medical records management and patient data search",
                "icon": "🏥",
                "sample_data_size": 100000
            },
            {
                "industry": "retail",
                "display_name": "Retail & E-Commerce",
                "description": "Product catalog and transaction analytics",
                "icon": "🛒",
                "sample_data_size": 100000
            },
            {
                "industry": "finance",
                "display_name": "Financial Services",
                "description": "Transaction monitoring and account management",
                "icon": "💰",
                "sample_data_size": 100000
            }
        ]
    
    return func.HttpResponse(
        json.dumps(industries),
        mimetype="application/json",
        status_code=200
    )


@app.route(route="industries/{industry}/queries", methods=["GET"])
def get_industry_queries(req: func.HttpRequest) -> func.HttpResponse:
    """Return example queries for a specific industry"""
    
    industry = req.route_params.get('industry')
    if not industry:
        return func.HttpResponse(
            json.dumps({"error": "Industry is required"}),
            mimetype="application/json",
            status_code=400,
        )
    
    queries_file = Path(__file__).parent.parent.parent / "industry-templates" / industry / "queries.json"
    
    if queries_file.exists():
        with open(queries_file, 'r') as f:
            queries_data = json.load(f)
            return func.HttpResponse(
                json.dumps(queries_data),
                mimetype="application/json",
                status_code=200
            )
    else:
        return func.HttpResponse(
            json.dumps({"error": f"Queries not found for industry: {industry}"}),
            mimetype="application/json",
            status_code=404
        )


@app.route(route="industries/{industry}/schema", methods=["GET"])
def get_industry_schema(req: func.HttpRequest) -> func.HttpResponse:
    """Return schema definition for a specific industry"""
    
    industry = req.route_params.get('industry')
    if not industry:
        return func.HttpResponse(
            json.dumps({"error": "Industry is required"}),
            mimetype="application/json",
            status_code=400,
        )
    
    schema_file = Path(__file__).parent.parent.parent / "industry-templates" / industry / "schema.json"
    
    if schema_file.exists():
        with open(schema_file, 'r') as f:
            schema_data = json.load(f)
            return func.HttpResponse(
                json.dumps(schema_data),
                mimetype="application/json",
                status_code=200
            )
    else:
        return func.HttpResponse(
            json.dumps({"error": f"Schema not found for industry: {industry}"}),
            mimetype="application/json",
            status_code=404
        )


@app.route(route="deployment/status", methods=["GET"])
def get_deployment_status(req: func.HttpRequest) -> func.HttpResponse:
    """Return deployment status and configuration"""
    
    status: dict[str, Any] = {
        "deployed": True,
        "hosting_service": os.environ.get("HOSTING_SERVICE", "container_apps"),
        "region": os.environ.get("AZURE_REGION", "eastus"),
        "mcp_endpoint": os.environ.get("MCP_ENDPOINT", "http://localhost:8000"),
        "industry": os.environ.get("SELECTED_INDUSTRY", "healthcare"),
        "timestamp": "2026-01-05T00:00:00Z"
    }
    
    return func.HttpResponse(
        json.dumps(status),
        mimetype="application/json",
        status_code=200
    )
