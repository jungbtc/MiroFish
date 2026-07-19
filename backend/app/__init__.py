"""
FOREFOLD Backend - Flask应用工厂
"""

import os
import hmac
import ipaddress
import re
import threading
import time
import warnings
from collections import defaultdict, deque

# 抑制 multiprocessing resource_tracker 的警告（来自第三方库如 transformers）
# 需要在所有其他导入之前设置
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, jsonify, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger
from .utils.private_data import safe_debug_payload
from .utils.safe_path import UnsafePathError, validate_identifier


def create_app(config_class=Config):
    """Flask应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 设置JSON编码：确保中文直接显示（而不是 \uXXXX 格式）
    # Flask >= 2.3 使用 app.json.ensure_ascii，旧版本使用 JSON_AS_ASCII 配置
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # 设置日志
    logger = setup_logger('mirofish')
    
    # 只在 reloader 子进程中打印启动信息（避免 debug 模式下打印两次）
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("FOREFOLD Backend 启动中...")
        logger.info("=" * 50)
    
    # v2 carries private decision metadata, so browser access is local/trusted-origin only.
    configured_v2_origins = os.environ.get("V2_CORS_ORIGINS", "")
    if configured_v2_origins:
        trusted_v2_origins = [
            origin.strip() for origin in configured_v2_origins.split(",") if origin.strip()
        ]
        cors_v2_origins = [re.escape(origin) for origin in trusted_v2_origins]
        v2_origin_rules_are_regex = False
    else:
        trusted_v2_origins = [
            r"^https?://localhost(?::\d+)?$",
            r"^https?://127\.0\.0\.1(?::\d+)?$",
            r"^https?://\[::1\](?::\d+)?$",
        ]
        cors_v2_origins = trusted_v2_origins
        v2_origin_rules_are_regex = True
    CORS(
        app,
        resources={
            r"/api/v2/.*": {"origins": cors_v2_origins},
            r"/api/(?!v2(?:/|$)).*": {"origins": "*"},
        },
    )

    v2_rate_buckets = defaultdict(deque)
    v2_rate_lock = threading.Lock()

    storage_id_fields = {"project_id", "simulation_id", "report_id", "run_id"}

    @app.before_request
    def reject_unsafe_storage_identifiers():
        """Reject unsafe route/body storage IDs before endpoint error handlers run."""
        candidates = dict(request.view_args or {})
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.is_json:
            body = request.get_json(silent=True)
            if isinstance(body, dict):
                for field in storage_id_fields:
                    if field in body and body[field] is not None:
                        candidates[field] = body[field]
        for field, value in candidates.items():
            if field not in storage_id_fields:
                continue
            try:
                validate_identifier(value, label=field.replace("_", " "))
            except UnsafePathError:
                return jsonify({"success": False, "error": "Invalid storage identifier."}), 400
        return None

    def _is_loopback_request() -> bool:
        try:
            address = ipaddress.ip_address(request.remote_addr or "")
            return address.is_loopback or bool(
                isinstance(address, ipaddress.IPv6Address)
                and address.ipv4_mapped
                and address.ipv4_mapped.is_loopback
            )
        except ValueError:
            return False

    def _provided_v2_key() -> str:
        authorization = request.headers.get("Authorization", "")
        if authorization.lower().startswith("bearer "):
            return authorization[7:].strip()
        return request.headers.get("X-MiroFish-Key", "").strip()

    def _trusted_v2_origin(origin: str) -> bool:
        for allowed in trusted_v2_origins:
            if origin == allowed:
                return True
            if v2_origin_rules_are_regex:
                try:
                    if re.fullmatch(allowed, origin):
                        return True
                except re.error:
                    continue
        return False

    @app.before_request
    def protect_private_v2_routes():
        """Keep private decision cases local unless explicit access is configured."""
        if not request.path.startswith("/api/v2/"):
            return None

        origin = request.headers.get("Origin")
        if origin and not _trusted_v2_origin(origin):
            return jsonify({"success": False, "error": "Origin is not trusted for v2 access."}), 403
        # Browsers do not send credentials on the CORS permission probe. The
        # actual request remains authenticated below; untrusted origins were
        # already rejected above.
        if request.method == "OPTIONS":
            return None

        configured_key = str(app.config.get("V2_API_KEY") or "")
        auth_required = (
            bool(configured_key)
            or bool(app.config.get("V2_REQUIRE_AUTH"))
            or not _is_loopback_request()
        )
        if auth_required:
            if not configured_key:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": (
                                "Non-loopback v2 access is disabled. Configure V2_API_KEY "
                                "or access the decision workspace locally."
                            ),
                        }
                    ),
                    403,
                )
            if not hmac.compare_digest(_provided_v2_key(), configured_key):
                return jsonify({"success": False, "error": "Valid v2 API credentials are required."}), 401

        if request.method == "POST" and request.path in {
            "/api/v2/run",
            "/api/v2/research-pack",
            "/api/v2/demo",
        }:
            limit = max(1, int(app.config.get("V2_RUN_RATE_LIMIT", 12)))
            window = max(1, int(app.config.get("V2_RATE_LIMIT_WINDOW_SECONDS", 60)))
            key = request.remote_addr or "unknown"
            now = time.monotonic()
            with v2_rate_lock:
                bucket = v2_rate_buckets[key]
                while bucket and bucket[0] <= now - window:
                    bucket.popleft()
                if len(bucket) >= limit:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Too many decision imports; retry after the rate-limit window.",
                            }
                        ),
                        429,
                    )
                bucket.append(now)
        return None
    
    # 注册模拟进程清理函数（确保服务器关闭时终止所有模拟进程）
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("已注册模拟进程清理函数")
    
    # 请求日志中间件
    @app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"请求: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            payload = (
                "[REDACTED_V2_REQUEST_PAYLOAD]"
                if request.path.startswith('/api/v2/')
                else safe_debug_payload(request.get_json(silent=True))
            )
            logger.debug(f"请求体: {payload}")
    
    @app.after_request
    def log_response(response):
        logger = get_logger('mirofish.request')
        logger.debug(f"响应: {response.status_code}")
        if request.path.startswith('/api/v2/'):
            response.headers['Cache-Control'] = 'no-store, private, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
    
    # 注册蓝图
    from .api import graph_bp, simulation_bp, report_bp, v2_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.register_blueprint(v2_bp, url_prefix='/api/v2')
    
    # 健康检查
    @app.route('/health')
    def health():
        core_configuration_errors = config_class.validate()
        return {
            'status': 'ok',
            'service': 'FOREFOLD Backend',
            'workflows': {
                'ontology_simulation': {
                    'status': (
                        'configuration_required'
                        if core_configuration_errors
                        else 'ready'
                    ),
                    'configuration_errors': core_configuration_errors,
                },
                'continuous_decision_workflow': {
                    'status': (
                        'configuration_required'
                        if core_configuration_errors
                        else 'ready'
                    ),
                    'stages': [
                        'ontology',
                        'simulation',
                        'initial_report',
                        'private_fact_refinement',
                        'final_report',
                    ],
                    'private_evidence_mode': 'local_deterministic',
                },
            },
        }
    
    if should_log_startup:
        logger.info("FOREFOLD Backend 启动完成")
    
    return app
