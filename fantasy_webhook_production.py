#!/usr/bin/env python3
"""
Fantasy News Center Webhook API - Production Version
Optimized for permanent deployment with proper error handling and logging
"""

from flask import Flask, request, jsonify
import json
import os
import sys
import traceback
from datetime import datetime
import requests
import subprocess
import shutil
import logging
from werkzeug.middleware.proxy_fix import ProxyFix

# Import the existing workflow functions
sys.path.append('/home/ubuntu')
from fantasy_news_center_workflow import get_sleeper_data, generate_json_report, download_user_avatars

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/webhook_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Configuration
GITHUB_TOKEN = "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"
GITHUB_REPO = "https://github.com/FNC570/Railway"
GITHUB_BRANCH = "main"

def get_current_nfl_week():
    """Get current NFL week (simplified version)"""
    current_date = datetime.now()
    # This is a simplified version - in production you might want more sophisticated logic
    if current_date.month >= 9 or (current_date.month <= 2):
        # Rough calculation - adjust as needed
        if current_date.month >= 9:
            week = min(((current_date.day - 7) // 7) + 1, 18)
        else:
            week = min(((current_date.day + 30) // 7) + 14, 18)
        return max(1, week)
    else:
        return 1  # Off-season default

def sanitize_filename(filename):
    """Sanitize filename for safe file system usage"""
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)  # Replace spaces with underscores
    filename = filename.strip('._')  # Remove leading/trailing dots and underscores
    return filename[:100]  # Limit length

def push_to_github_dynamic(filename, league_name, week):
    """
    Push the generated JSON file to GitHub repository with dynamic naming
    
    Args:
        filename (str): Local filename of the JSON file
        league_name (str): Name of the league for GitHub filename
        week (int): Week number
    
    Returns:
        tuple: (success: bool, result: str)
    """
    try:
        # Create sanitized filename for GitHub
        sanitized_league_name = sanitize_filename(league_name)
        github_filename = f"{sanitized_league_name}_week{week}.json"
        
        # Create authenticated URL
        auth_url = GITHUB_REPO.replace("https://", f"https://{GITHUB_TOKEN}@")
        
        # Clone or update repository
        repo_dir = "/tmp/fnc_repo_dynamic"
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
        
        logger.info(f"Cloning repository for {github_filename}...")
        result = subprocess.run([
            "git", "clone", "-b", GITHUB_BRANCH, auth_url, repo_dir
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Git clone failed: {result.stderr}")
            return False, f"Git clone failed: {result.stderr}"
        
        # Copy the JSON file to the repository with new name
        source_file = os.path.join("/home/ubuntu", filename)
        dest_file = os.path.join(repo_dir, github_filename)
        shutil.copy2(source_file, dest_file)
        logger.info(f"Copied {filename} to {github_filename} in repository")
        
        # Configure git user (required for commits)
        subprocess.run([
            "git", "config", "user.email", "ralphmartinojr@outlook.com"
        ], cwd=repo_dir, capture_output=True)
        subprocess.run([
            "git", "config", "user.name", "Fantasy News Center Bot"
        ], cwd=repo_dir, capture_output=True)
        
        # Add, commit, and push
        subprocess.run(["git", "add", github_filename], cwd=repo_dir, capture_output=True)
        
        commit_message = f"Fantasy Report - {league_name} Week {week} - {datetime.now().strftime('%Y-%m-%d %H:%M PST')}"
        result = subprocess.run([
            "git", "commit", "-m", commit_message
        ], cwd=repo_dir, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Git commit failed: {result.stderr}")
            return False, f"Git commit failed: {result.stderr}"
        
        result = subprocess.run([
            "git", "push", "origin", GITHUB_BRANCH
        ], cwd=repo_dir, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Git push failed: {result.stderr}")
            return False, f"Git push failed: {result.stderr}"
        
        logger.info(f"Successfully pushed {github_filename} to GitHub!")
        
        # Clean up
        shutil.rmtree(repo_dir)
        return True, github_filename
        
    except Exception as e:
        logger.error(f"Error pushing to GitHub: {e}")
        return False, str(e)

@app.route('/', methods=['GET'])
def home():
    """Home page with API documentation"""
    return jsonify({
        "service": "Fantasy News Center Webhook API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "GET /health",
            "generate_report": "POST /generate-report",
            "alternative": "GET /leagues/<league_id>/week/<week>"
        },
        "documentation": "https://github.com/FNC570/FNC",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Fantasy News Center Webhook API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "uptime": "operational"
    })

@app.route('/generate-report', methods=['POST'])
def generate_report():
    """
    Generate fantasy report for a given league ID
    
    Expected JSON payload:
    {
        "league_id": "1235357902219247616",
        "week": 3 (optional - will use current week if not provided),
        "push_to_github": true (optional - defaults to true)
    }
    """
    start_time = datetime.now()
    
    try:
        # Parse request data
        data = request.get_json()
        
        if not data:
            logger.warning("No JSON data provided in request")
            return jsonify({
                "error": "No JSON data provided",
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }), 400
        
        league_id = data.get('league_id')
        if not league_id:
            logger.warning("league_id missing from request")
            return jsonify({
                "error": "league_id is required",
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }), 400
        
        # Get week (use provided or current)
        week = data.get('week')
        if not week:
            week = get_current_nfl_week()
        
        push_to_github = data.get('push_to_github', True)
        
        logger.info(f"Processing request for League ID: {league_id}, Week: {week}")
        
        # Fetch data from Sleeper API
        logger.info("Fetching data from Sleeper API...")
        sleeper_data = get_sleeper_data("", "nfl", "2025", league_id, week)
        
        if not sleeper_data or not sleeper_data.get("matchups"):
            logger.error(f"Failed to fetch league data for {league_id}")
            return jsonify({
                "error": "Failed to fetch league data or no matchups found",
                "status": "error",
                "league_id": league_id,
                "week": week,
                "timestamp": datetime.now().isoformat()
            }), 404
        
        # Get league name for filename
        league_name = "Unknown_League"
        if sleeper_data.get("league_details") and sleeper_data["league_details"].get("name"):
            league_name = sleeper_data["league_details"]["name"]
        
        logger.info(f"League found: {league_name}")
        
        # Download avatars
        logger.info("Downloading user avatars...")
        if sleeper_data.get("users"):
            avatar_paths = download_user_avatars(sleeper_data["users"])
            logger.info(f"Downloaded {len(avatar_paths)} avatars")
        
        # Generate JSON report
        logger.info("Generating JSON report...")
        json_report = generate_json_report(sleeper_data, week)
        
        # Create filename based on league name and week
        sanitized_league_name = sanitize_filename(league_name)
        local_filename = f"{sanitized_league_name}_week{week}.json"
        
        # Save JSON file locally
        local_filepath = os.path.join("/home/ubuntu", local_filename)
        with open(local_filepath, "w") as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Generated JSON report saved to {local_filename}")
        
        # Push to GitHub if requested
        github_filename = None
        github_error = None
        if push_to_github:
            logger.info("Pushing to GitHub repository...")
            github_success, github_result = push_to_github_dynamic(local_filename, league_name, week)
            if github_success:
                github_filename = github_result
                logger.info(f"Successfully pushed to GitHub as {github_filename}")
            else:
                github_error = github_result
                logger.error(f"GitHub push failed: {github_error}")
        
        # Calculate processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Prepare response
        response_data = {
            "status": "success",
            "message": "Fantasy report generated successfully",
            "data": {
                "league_id": league_id,
                "league_name": league_name,
                "week": week,
                "local_filename": local_filename,
                "report_data": json_report,
                "generated_timestamp": datetime.now().isoformat(),
                "processing_time_seconds": round(processing_time, 2),
                "matchups_count": len(json_report.get("matchups", [])),
                "injured_players": json_report.get("injury_report", {}).get("total_injured_players", 0),
                "next_week_matchups": len(json_report.get("next_week_preview", {}).get("matchups", [])),
                "trending_adds": len(json_report.get("waiver_wire_watch", {}).get("hot_pickups", [])),
                "trending_drops": len(json_report.get("waiver_wire_watch", {}).get("falling_stars", []))
            }
        }
        
        # Add GitHub info if applicable
        if push_to_github:
            response_data["data"]["github"] = {
                "pushed": github_filename is not None,
                "filename": github_filename,
                "error": github_error
            }
        
        logger.info(f"Request completed successfully in {processing_time:.2f} seconds")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Internal server error: {str(e)}",
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/leagues/<league_id>/week/<int:week>', methods=['GET'])
def generate_report_get(league_id, week):
    """
    Alternative GET endpoint for generating reports
    Usage: GET /leagues/1235357902219247616/week/3
    """
    # Convert GET request to POST-like data
    fake_data = {
        "league_id": league_id,
        "week": week,
        "push_to_github": request.args.get('push_to_github', 'true').lower() == 'true'
    }
    
    # Temporarily replace request data
    original_get_json = request.get_json
    request.get_json = lambda: fake_data
    
    try:
        return generate_report()
    finally:
        request.get_json = original_get_json

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "status": "error",
        "available_endpoints": [
            "GET /health",
            "POST /generate-report", 
            "GET /leagues/<league_id>/week/<week>"
        ],
        "timestamp": datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "status": "error",
        "timestamp": datetime.now().isoformat()
    }), 500

if __name__ == '__main__':
    logger.info("Starting Fantasy News Center Webhook API (Production)")
    logger.info("Endpoints available:")
    logger.info("  GET  / - API documentation")
    logger.info("  GET  /health - Health check")
    logger.info("  POST /generate-report - Generate fantasy report")
    logger.info("  GET  /leagues/<league_id>/week/<week> - Alternative endpoint")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
