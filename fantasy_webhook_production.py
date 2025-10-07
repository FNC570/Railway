#!/usr/bin/env python3
"""
Fantasy News Center Webhook API (Production, no avatars)
- POST /generate-report  { league_id: "...", week?: int, push_to_github?: bool, github_repo?: "owner/repo", github_path_prefix?: "reports/" }
- GET  /leagues/<league_id>/week/<int:week>
"""

from flask import Flask, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timezone
import base64
import json
import logging
import os
import traceback
import requests

# Local imports (refactored workflow)
from fantasy_news_center_workflow import (
    get_sleeper_data,
    generate_json_report,
    current_nfl_week,
)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s"
)
log = logging.getLogger("fnc-webhook")

REQ_TIMEOUT = 15


def sanitize_filename(filename: str) -> str:
    import re
    s = re.sub(r'[<>:"/\\|?*]+', "_", filename)
    s = re.sub(r"\s+", "_", s).strip("._")
    return s[:100] if len(s) > 100 else s


def push_to_github_contents_api(
    token: str,
    repo: str,
    path: str,
    content_bytes: bytes,
    commit_message: str,
    branch: str = "main",
) -> tuple[bool, str]:
    """
    Use GitHub Contents API to create/update a file without embedding PAT in a git remote.
    repo: "owner/repo"
    path: "dir/file.json"
    """
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    # check if file exists to fetch sha
    sha = None
    try:
        r = requests.get(url, headers=headers, timeout=REQ_TIMEOUT, params={"ref": branch})
        if r.status_code == 200:
            sha = r.json().get("sha")
    except requests.RequestException:
        pass

    payload = {
        "message": commit_message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    try:
        resp = requests.put(url, headers=headers, data=json.dumps(payload), timeout=REQ_TIMEOUT)
        if resp.status_code in (200, 201):
            return True, path
        return False, f"GitHub API error {resp.status_code}: {resp.text[:300]}"
    except requests.RequestException as e:
        return False, f"GitHub request failed: {e}"


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Fantasy News Center Webhook API",
        "version": "2.0.0-no-avatars",
        "status": "operational",
        "endpoints": {
            "health": "GET /health",
            "generate_report": "POST /generate-report",
            "alt_generate": "GET /leagues/<league_id>/week/<week>"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "Fantasy News Center Webhook API",
        "version": "2.0.0-no-avatars",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@app.route("/generate-report", methods=["POST"])
def generate_report():
    started = datetime.now(timezone.utc)
    try:
        body = request.get_json(silent=True) or {}
        league_id = body.get("league_id")
        if not league_id:
            return jsonify({"status": "error", "error": "league_id is required"}), 400

        week = int(body["week"]) if "week" in body and isinstance(body["week"], int) else current_nfl_week()
        push = bool(body.get("push_to_github", True))
        repo = body.get("github_repo") or os.getenv("GITHUB_REPO")  # "owner/repo"
        branch = os.getenv("GITHUB_BRANCH", "main")
        path_prefix = body.get("github_path_prefix", "").strip("/")
        token = os.getenv("GITHUB_TOKEN")

        log.info(f"Generating report league={league_id} week={week} push={push}")

        data = get_sleeper_data("", "nfl", str(datetime.now().year), league_id, week)
        if not data or not data.get("matchups"):
            return jsonify({
                "status": "error",
                "error": "Failed to fetch league data or no matchups found",
                "league_id": league_id,
                "week": week
            }), 404

        league_name = (data.get("league_details") or {}).get("name") or f"league_{league_id}"
        json_report = generate_json_report(data, week)
        serialized = json.dumps(json_report, indent=2, ensure_ascii=False).encode("utf-8")

        # optional GitHub push
        gh_result = {"pushed": False}
        if push:
            if not (token and repo):
                gh_result["error"] = "Missing GITHUB_TOKEN or github_repo"
            else:
                safe_name = sanitize_filename(league_name)
                file_name = f"{safe_name}_week{week}.json"
                full_path = f"{path_prefix}/{file_name}" if path_prefix else file_name
                ok, msg = push_to_github_contents_api(
                    token=token,
                    repo=repo,
                    path=full_path,
                    content_bytes=serialized,
                    commit_message=f"Fantasy Report - {league_name} - Week {week}",
                    branch=branch,
                )
                gh_result.update({"pushed": ok, "path": msg if ok else None, "error": None if ok else msg})

        took = (datetime.now(timezone.utc) - started).total_seconds()
        return jsonify({
            "status": "success",
            "message": "Fantasy report generated",
            "data": {
                "league_id": league_id,
                "league_name": league_name,
                "week": week,
                "report": json_report,
                "processing_time_seconds": round(took, 2),
                "github": gh_result if push else {"pushed": False}
            }
        }), 200

    except Exception as e:
        log.error("Unhandled error: %s", e)
        log.debug(traceback.format_exc())
        return jsonify({"status": "error", "error": "Internal server error"}), 500


@app.route("/leagues/<league_id>/week/<int:week>", methods=["GET"])
def generate_report_get(league_id, week):
    # Delegate to POST handler with constructed body
    with app.test_request_context(
        "/generate-report",
        method="POST",
        json={"league_id": league_id, "week": week, "push_to_github": request.args.get("push_to_github", "true").lower() == "true"},
    ):
        return generate_report()


@app.errorhandler(404)
def not_found(_):
    return jsonify({
        "status": "error",
        "error": "Endpoint not found",
        "available_endpoints": ["GET /", "GET /health", "POST /generate-report", "GET /leagues/<league_id>/week/<week>"]
    }), 404


if __name__ == "__main__":
    log.info("Starting Fantasy News Center Webhook API (no avatars)")
    app.run(host="0.0.0.0", port=5000, debug=False)
