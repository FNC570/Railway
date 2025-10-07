import requests
import json
import random
from datetime import datetime
import os
import subprocess
import shutil
from download_avatars import download_user_avatars, get_avatar_info

# --- Sleeper Data Pull and Script Generation Functions ---
def get_sleeper_data(user_id, sport, season, league_id, week):
    base_url = "https://api.sleeper.app/v1/"

    league_url = f"{base_url}league/{league_id}"
    league_response = requests.get(league_url)
    league_data = league_response.json()

    rosters_url = f"{base_url}league/{league_id}/rosters"
    rosters_response = requests.get(rosters_url)
    rosters_data = rosters_response.json()

    users_url = f"{base_url}league/{league_id}/users"
    users_response = requests.get(users_url)
    users_data = users_response.json()

    matchups_url = f"{base_url}league/{league_id}/matchups/{week}"
    matchups_response = requests.get(matchups_url)
    matchups_data = matchups_response.json()

    # Get next week's matchups
    next_week = week + 1
    next_matchups_url = f"{base_url}league/{league_id}/matchups/{next_week}"
    next_matchups_response = requests.get(next_matchups_url)
    next_matchups_data = next_matchups_response.json() if next_matchups_response.status_code == 200 else []

    players_url = f"{base_url}players/nfl"
    players_response = requests.get(players_url)
    players_data = players_response.json()

    # Get trending players (adds and drops)
    trending_adds_url = f"{base_url}players/nfl/trending/add"
    trending_adds_response = requests.get(trending_adds_url)
    trending_adds_data = trending_adds_response.json() if trending_adds_response.status_code == 200 else []

    trending_drops_url = f"{base_url}players/nfl/trending/drop"
    trending_drops_response = requests.get(trending_drops_url)
    trending_drops_data = trending_drops_response.json() if trending_drops_response.status_code == 200 else []

    # Process player data for easier access
    player_id_to_name = {p_id: p_data["full_name"] for p_id, p_data in players_data.items() if "full_name" in p_data}
    player_id_to_injury_info = {p_id: p_data for p_id, p_data in players_data.items() if p_data.get("injury_status") is not None and p_data.get("injury_status") != "Active"}

    return {
        "league_details": league_data,
        "rosters": rosters_data,
        "users": users_data,
        "matchups": matchups_data,
        "next_matchups": next_matchups_data,
        "players": players_data,
        "player_id_to_name": player_id_to_name,
        "player_id_to_injury_info": player_id_to_injury_info,
        "trending_adds": trending_adds_data,
        "trending_drops": trending_drops_data
    }

def generate_report_script(data, week):
    if not data or not data["matchups"] or not data["users"] or not data["rosters"] or not data["players"]:
        return "Could not generate report due to missing data."

    report_lines = []
    report_lines.append(f"Welcome back, fantasy fanatics! Week {week} is in the books, and wow… it gave us plenty to laugh at, cry about, and maybe even brag over. Let’s dive in.\n")

    league_name = data["league_details"]["name"] if data["league_details"] and data["league_details"]["name"] else "Your Fantasy League"

    user_map = {user["user_id"]: user["display_name"] for user in data["users"]}
    roster_to_user = {roster["roster_id"]: roster["owner_id"] for roster in data["rosters"]}
    player_id_to_name = {p_id: p_data["full_name"] for p_id, p_data in data["players"].items() if "full_name" in p_data}
    player_id_to_team = {p_id: p_data["team"] for p_id, p_data in data["players"].items() if "team" in p_data}
    
    # Filter for players with injury status
    player_id_to_injury_info = {p_id: p_data for p_id, p_data in data["players"].items() if p_data.get("injury_status") is not None and p_data.get("injury_status") != "Active"}

    # Sarcastic phrases for blowouts and nail-biters
    blowout_phrases_score = [
        "  That’s not a win… that’s a clinic. {winner_name} gets the highlight reel, {loser_name} gets… well, a pat on the back.\n",
        "  That’s a {score_diff:.2f}-point beatdown. One was playing chess, the other… maybe tic-tac-toe.\n",
        "  A monumental {score_diff:.2f}-point victory! The losing team is probably still looking for their dignity.\n",
        "  A {score_diff:.2f}-point shellacking! Clearly, one team was playing checkers while the other was playing chess... badly.\n"
    ]
    blowout_phrases_sarcastic = [
        "  Well, that was a \"blowout\"! {loser_name} clearly forgot to invite the other team to the game.\n",
        "  {winner_name} absolutely dominated {loser_name}. I think {loser_name} might need a new hobby after that performance.\n",
        "  It wasn\"t even close! {loser_name} put up a valiant effort... if by valiant you mean \"barely tried\".\n",
        "  {winner_name} delivered a masterclass in fantasy football, while {loser_name} delivered... well, a participation trophy.\n"
    ]
    nailbiter_phrases = [
        "  Not flashy, but a win’s a win. {loser_name} might be questioning their draft board after this one.\n",
        "  Phew! That was close. So close, in fact, I almost spilled my beverage. A true test of fantasy endurance.\n",
        "  A real cliffhanger! The tension was thicker than a Sunday morning pancake. Someone barely escaped with a win.\n",
        "  This game had more twists and turns than a pretzel factory. A truly agonizing (or exhilarating) finish!\n"
    ]

    matchup_groups = {}
    for matchup in data["matchups"]:
        matchup_id = matchup["matchup_id"]
        if matchup_id not in matchup_groups:
            matchup_groups[matchup_id] = []
        matchup_groups[matchup_id].append(matchup)

    for matchup_id, teams in matchup_groups.items():
        if len(teams) == 2:
            team1 = teams[0]
            team2 = teams[1]

            team1_owner_id = roster_to_user.get(team1["roster_id"])
            team2_owner_id = roster_to_user.get(team2["roster_id"])

            team1_name = user_map.get(team1_owner_id, f"Unknown User ({team1_owner_id})")
            team2_name = user_map.get(team2_owner_id, f"Unknown User ({team2_owner_id})")

            score_diff = abs(team1["points"] - team2["points"])
            winner_name = team1_name if team1["points"] > team2["points"] else team2_name
            loser_name = team2_name if team1["points"] > team2["points"] else team1_name

            report_lines.append(f"\nMatchup {matchup_id}:\n")
            report_lines.append("  {} put up {:.2f} points against {}\'s {:.2f} points.\n".format(team1_name, team1["points"], team2_name, team2["points"]))

            if score_diff >= 30:
                if random.random() < 0.75: # 75% chance to use score-based phrase
                    report_lines.append(random.choice(blowout_phrases_score).format(score_diff=score_diff, winner_name=winner_name, loser_name=loser_name))
                else:
                    report_lines.append(random.choice(blowout_phrases_sarcastic).format(score_diff=score_diff, winner_name=winner_name, loser_name=loser_name))
            elif score_diff <= 5:
                report_lines.append(random.choice(nailbiter_phrases).format(winner_name=winner_name, loser_name=loser_name))
            else:
                report_lines.append(f"  A solid win for {winner_name}. The other team will surely be rethinking their life choices this week.\n")

            # Player projection callouts (mocked for now)
            report_lines.append("  🔥 Projection Obliterator: ")
            winning_team_starters = team1["starters"] if team1["points"] > team2["points"] else team2["starters"]
            if winning_team_starters:
                highlight_player_id = random.choice(winning_team_starters) # Randomly pick one starter
                highlight_player_name = player_id_to_name.get(highlight_player_id, "a mysterious superstar")
                report_lines.append(f"{highlight_player_name}, proving once again why they’re a fantasy cheat code.\n")
            else:
                report_lines.append("Someone, somewhere, probably blew past their projection. Details are for the weak.\n")

    # Injury Report Section
    report_lines.append("\n--- Injury Report ---\n")
    injured_players_found = False
    # Limit to a few notable injured players to avoid exceeding character limits
    notable_injured_players = list(player_id_to_injury_info.values())[:5] # Get up to 5 injured players

    if notable_injured_players:
        injured_players_found = True
        for player_info in notable_injured_players:
            player_name = player_info.get("full_name", "A player")
            injury_status = player_info.get("injury_status", "Questionable")
            injury_body_part = player_info.get("injury_body_part", "an undisclosed ailment")
            team_abbr = player_info.get("team")
            if team_abbr is None:
                team_display = "a free agent"
            else:
                team_display = team_abbr

            injury_commentary = [
                f"  **Injury Update:** It seems {player_name} is taking an unscheduled vacation due to a {injury_body_part} issue. His team, {team_display}, will surely miss his... well, his presence on the field.\n",
                f"  **On the Mend (or Not):** {player_name} is currently listed as {injury_status}. Let's hope for a speedy recovery, or at least a recovery before the fantasy playoffs. {team_display} holds its breath.\n",
                f"  Another one bites the dust! {player_name} is out with a {injury_body_part}. Just when {team_display} thought things couldn't get worse.\n"
            ]
            report_lines.append(random.choice(injury_commentary))
        
        if len(player_id_to_injury_info) > 5:
            report_lines.append(f"  And that\"s just the tip of the iceberg! {len(player_id_to_injury_info) - 5} more players are nursing various ailments. Good luck with your waiver wire claims!\n")

    if not injured_players_found:
        report_lines.append("  Surprisingly, everyone is miraculously healthy. Or perhaps, no one important got hurt. Either way, less drama for us.\n")

    # Next Week Preview Section
    if data.get("next_matchups"):
        report_lines.append(f"\n--- Looking Ahead: Week {week + 1} Preview ---\n")
        next_matchup_groups = {}
        for matchup in data["next_matchups"]:
            matchup_id = matchup["matchup_id"]
            if matchup_id not in next_matchup_groups:
                next_matchup_groups[matchup_id] = []
            next_matchup_groups[matchup_id].append(matchup)
        
        preview_count = 0
        for matchup_id, teams in next_matchup_groups.items():
            if len(teams) == 2 and preview_count < 3:  # Show up to 3 preview matchups
                team1, team2 = teams
                user1_id = roster_to_user.get(team1["roster_id"])
                user2_id = roster_to_user.get(team2["roster_id"])
                user1_name = user_map.get(user1_id, "Unknown")
                user2_name = user_map.get(user2_id, "Unknown")
                
                preview_phrases = [
                    f"  {user1_name} vs {user2_name} - This could get interesting... or not.\n",
                    f"  {user1_name} takes on {user2_name} - Someone's going to regret their lineup decisions.\n",
                    f"  {user1_name} faces {user2_name} - May the best waiver wire pickup win!\n"
                ]
                report_lines.append(random.choice(preview_phrases))
                preview_count += 1
        
        if preview_count == 0:
            report_lines.append("  Next week's matchups are still being determined. Stay tuned for more chaos!\n")

    # Trending Players Section
    trending_section_added = False
    
    if data.get("trending_adds") and len(data["trending_adds"]) > 0:
        if not trending_section_added:
            report_lines.append(f"\n--- Waiver Wire Watch ---\n")
            trending_section_added = True
        
        report_lines.append("  **Hot Pickups:** ")
        top_adds = data["trending_adds"][:3]  # Top 3 trending adds
        add_names = []
        for add_data in top_adds:
            player_id = add_data.get("player_id")
            if player_id and player_id in player_id_to_name:
                add_names.append(player_id_to_name[player_id])
        
        if add_names:
            if len(add_names) == 1:
                report_lines.append(f"{add_names[0]} is flying off the waiver wire faster than free pizza at a college dorm.\n")
            else:
                report_lines.append(f"{', '.join(add_names[:-1])} and {add_names[-1]} are the hot commodities everyone's chasing. Good luck with that FAAB budget!\n")
    
    if data.get("trending_drops") and len(data["trending_drops"]) > 0:
        if not trending_section_added:
            report_lines.append(f"\n--- Waiver Wire Watch ---\n")
            trending_section_added = True
        
        report_lines.append("  **Falling Stars:** ")
        top_drops = data["trending_drops"][:3]  # Top 3 trending drops
        drop_names = []
        for drop_data in top_drops:
            player_id = drop_data.get("player_id")
            if player_id and player_id in player_id_to_name:
                drop_names.append(player_id_to_name[player_id])
        
        if drop_names:
            if len(drop_names) == 1:
                report_lines.append(f"{drop_names[0]} is being dropped faster than a bad habit. Ouch.\n")
            else:
                report_lines.append(f"{', '.join(drop_names[:-1])} and {drop_names[-1]} are getting the boot from fantasy rosters everywhere. Time to find new heroes!\n")

    report_lines.append(f"\nAnd that's your Week {week} wrap-up from the {league_name} league! Some crushed it, some got crushed, and the rest… well, better luck next week. Until then, keep the smack talk coming — it's half the fun of fantasy.\n")
    return "".join(report_lines)

# --- JSON Report Generation Function ---
def generate_json_report(data, week):
    """
    Generate a structured JSON report from Sleeper data
    
    Args:
        data (dict): Sleeper data containing matchups, users, etc.
        week (int): Week number
    
    Returns:
        dict: Structured JSON report
    """
    league_name = data.get("league", {}).get("name", "FUCC")
    matchups = data.get("matchups", [])
    users = data.get("users", [])
    rosters = data.get("rosters", [])
    player_id_to_name = data.get("player_id_to_name", {})
    player_id_to_injury_info = data.get("player_id_to_injury_info", {})
    
    # Create user and roster mappings
    user_map = {user["user_id"]: user["display_name"] for user in users}
    roster_to_user = {roster["roster_id"]: roster["owner_id"] for roster in rosters}
    
    # Group matchups
    matchup_groups = {}
    for matchup in matchups:
        matchup_id = matchup["matchup_id"]
        if matchup_id not in matchup_groups:
            matchup_groups[matchup_id] = []
        matchup_groups[matchup_id].append(matchup)
    
    # Build JSON structure
    json_report = {
        "report_metadata": {
            "league_name": league_name,
            "week": week,
            "generated_timestamp": datetime.now().isoformat() + "Z",
            "report_type": "automated_json",
            "version": "enhanced_v3"
        },
        "matchups": [],
        "injury_report": {
            "featured_injuries": [],
            "total_injured_players": len(player_id_to_injury_info)
        },
        "next_week_preview": {
            "week": week + 1,
            "matchups": []
        },
        "waiver_wire_watch": {
            "hot_pickups": [],
            "falling_stars": []
        }
    }
    
    # Process matchups
    for matchup_id, teams in matchup_groups.items():
        if len(teams) == 2:
            team1, team2 = teams
            user1_id = roster_to_user.get(team1["roster_id"])
            user2_id = roster_to_user.get(team2["roster_id"])
            user1_name = user_map.get(user1_id, "Unknown")
            user2_name = user_map.get(user2_id, "Unknown")
            
            points1 = team1.get("points", 0)
            points2 = team2.get("points", 0)
            point_diff = abs(points1 - points2)
            
            matchup_data = {
                "matchup_id": matchup_id,
                "team1": {
                    "name": user1_name,
                    "points": points1,
                    "result": "win" if points1 > points2 else "loss"
                },
                "team2": {
                    "name": user2_name,
                    "points": points2,
                    "result": "win" if points2 > points1 else "loss"
                },
                "point_difference": round(point_diff, 2),
                "matchup_type": "blowout" if point_diff > 30 else "close_game"
            }
            json_report["matchups"].append(matchup_data)
    
    # Add injury report
    notable_injured = list(player_id_to_injury_info.values())[:5]
    for player_info in notable_injured:
        injury_data = {
            "player": player_info.get("full_name", "Unknown"),
            "status": player_info.get("injury_status", "Unknown"),
            "injury": player_info.get("injury_body_part", "Unknown"),
            "team": player_info.get("team", "free agent")
        }
        json_report["injury_report"]["featured_injuries"].append(injury_data)
    
    # Add next week preview if available
    if data.get("next_matchups"):
        next_matchup_groups = {}
        for matchup in data["next_matchups"]:
            matchup_id = matchup["matchup_id"]
            if matchup_id not in next_matchup_groups:
                next_matchup_groups[matchup_id] = []
            next_matchup_groups[matchup_id].append(matchup)
        
        for matchup_id, teams in next_matchup_groups.items():
            if len(teams) == 2:
                team1, team2 = teams
                user1_id = roster_to_user.get(team1["roster_id"])
                user2_id = roster_to_user.get(team2["roster_id"])
                user1_name = user_map.get(user1_id, "Unknown")
                user2_name = user_map.get(user2_id, "Unknown")
                
                preview_data = {
                    "team1": user1_name,
                    "team2": user2_name,
                    "matchup_id": matchup_id
                }
                json_report["next_week_preview"]["matchups"].append(preview_data)
    
    # Add trending players if available
    if data.get("trending_adds"):
        for add_data in data["trending_adds"][:3]:
            player_id = add_data.get("player_id")
            if player_id and player_id in player_id_to_name:
                json_report["waiver_wire_watch"]["hot_pickups"].append({
                    "player": player_id_to_name[player_id],
                    "count": add_data.get("count", 0)
                })
    
    if data.get("trending_drops"):
        for drop_data in data["trending_drops"][:3]:
            player_id = drop_data.get("player_id")
            if player_id and player_id in player_id_to_name:
                json_report["waiver_wire_watch"]["falling_stars"].append({
                    "player": player_id_to_name[player_id],
                    "count": drop_data.get("count", 0)
                })
    
    return json_report

# --- GitHub Push Function ---
def push_to_github(filename, week):
    """
    Push the generated JSON file to GitHub repository
    
    Args:
        filename (str): Name of the JSON file to push
        week (int): Week number for commit message
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # GitHub repository details
        repo_url = "https://github.com/FNC570/FNC.git"
        branch = "main"
        github_token = "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"
        
        # Create authenticated URL
        auth_url = repo_url.replace("https://", f"https://{github_token}@")
        
        # Clone or update repository
        repo_dir = "/tmp/fnc_repo"
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
        
        print(f"Cloning repository...")
        result = subprocess.run([
            "git", "clone", "-b", branch, auth_url, repo_dir
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Git clone failed: {result.stderr}")
            return False
        
        # Copy the JSON file to the repository
        source_file = os.path.join("/home/ubuntu", filename)
        dest_file = os.path.join(repo_dir, filename)
        shutil.copy2(source_file, dest_file)
        print(f"Copied {filename} to repository")
        
        # Configure git user (required for commits)
        subprocess.run([
            "git", "config", "user.email", "ralphmartinojr@outlook.com"
        ], cwd=repo_dir, capture_output=True)
        subprocess.run([
            "git", "config", "user.name", "Fantasy News Center Bot"
        ], cwd=repo_dir, capture_output=True)
        
        # Add, commit, and push
        subprocess.run(["git", "add", filename], cwd=repo_dir, capture_output=True)
        
        commit_message = f"Automated Fantasy Report - Week {week} - {datetime.now().strftime('%Y-%m-%d %H:%M PST')}"
        result = subprocess.run([
            "git", "commit", "-m", commit_message
        ], cwd=repo_dir, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Git commit failed: {result.stderr}")
            return False
        
        result = subprocess.run([
            "git", "push", "origin", branch
        ], cwd=repo_dir, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Git push failed: {result.stderr}")
            return False
        
        print(f"Successfully pushed {filename} to GitHub!")
        
        # Clean up
        shutil.rmtree(repo_dir)
        return True
        
    except Exception as e:
        print(f"Error pushing to GitHub: {e}")
        return False

# --- ElevenLabs Audio Generation Function ---
def generate_audio(text, voice_id="21m00Tcm4TlvDq8ikWAM", output_filename="output.mp3"):
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("ELEVENLABS_API_KEY environment variable not set.")
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_v3", # This is the v3 model ID. Note: It might be 'eleven_v3' or 'eleven_v3_alpha' depending on the exact version. I will use 'eleven_v3' as per documentation.
        "model_id": "eleven_v3",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors

        with open(output_filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        print(f"Audio generated successfully and saved to {output_filename}")
        return output_filename
    except requests.exceptions.RequestException as e:
        print(f"Error generating audio: {e}")
        if response is not None:
            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.text}")
        return None

# --- Main Workflow Execution ---
if __name__ == "__main__":
    # Configuration
    example_user_id = "483459259485384704" # User ID for \"sleeperuser\"
    example_sport = "nfl"
    example_season = "2023"
    original_league_id = "1235357902219247616" # Original user provided league ID

    # Dynamically determine the current NFL week
    today = datetime.now()
    week1_start_2025 = datetime(2025, 9, 4) # Assuming NFL Week 1 starts on Sept 4, 2025
    days_since_week1 = (today - week1_start_2025).days
    current_nfl_week = (days_since_week1 // 7) + 1
    if current_nfl_week < 1:
        current_nfl_week = 1
    elif current_nfl_week > 18:
        current_nfl_week = 18

    # For immediate test runs, explicitly set to Week 2 as requested.
    # The scheduled task will use the dynamic `current_nfl_week`.
    example_week = 3 # Week 3 for Tuesday 05:30 PST scheduled run
    example_league_id = original_league_id # Ensure original league ID is used for scheduled task

    # For the actual scheduled task, the dynamic week calculation would be used:
    # example_week = current_nfl_week

    print(f"Starting Fantasy News Center workflow for League ID: {example_league_id}, Week: {example_week}")

    # 1. Pull data from Sleeper API
    print("Fetching data from Sleeper API...")
    sleeper_data = get_sleeper_data(example_user_id, example_sport, example_season, example_league_id, example_week)

    if sleeper_data:
        # 2. Download user avatars
        print("Downloading user avatars...")
        avatar_paths = download_user_avatars(sleeper_data["users"])
        print(f"Downloaded {len(avatar_paths)} avatars to /home/ubuntu/avatars/")
        
        # 3. Generate the JSON report
        print("Generating JSON report...")
        json_report = generate_json_report(sleeper_data, example_week)
        
        # Save JSON file locally
        json_filename = f"fucc_league_week{example_week}.json"
        with open(json_filename, "w") as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)
        print(f"Generated JSON report saved to {json_filename}")
        
        # 4. Push to GitHub
        print("Pushing to GitHub repository...")
        github_success = push_to_github(json_filename, example_week)
        if github_success:
            print("✅ Successfully pushed to GitHub!")
        else:
            print("❌ Failed to push to GitHub")
    else:
        print("Failed to retrieve Sleeper data. Workflow aborted.")

