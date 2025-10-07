# fantasy_news_center_workflow.py
import json
import os
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, List

import requests

SLEEPER_BASE = "https://api.sleeper.app/v1/"
REQ_TIMEOUT = 15  # seconds


class SleeperError(RuntimeError):
    pass


def _get(url: str) -> Any:
    try:
        resp = requests.get(url, timeout=REQ_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise SleeperError(f"HTTP error calling {url}: {e}") from e
    except ValueError as e:
        raise SleeperError(f"Non-JSON response from {url}: {e}") from e


def get_sleeper_data(user_id: str, sport: str, season: str, league_id: str, week: int) -> Dict[str, Any]:
    """Fetch core league data for a given week from Sleeper."""
    league_data = _get(f"{SLEEPER_BASE}league/{league_id}")
    rosters_data = _get(f"{SLEEPER_BASE}league/{league_id}/rosters")
    users_data = _get(f"{SLEEPER_BASE}league/{league_id}/users")
    matchups_data = _get(f"{SLEEPER_BASE}league/{league_id}/matchups/{week}")

    next_week = week + 1
    try:
        next_matchups_data = _get(f"{SLEEPER_BASE}league/{league_id}/matchups/{next_week}")
        if not isinstance(next_matchups_data, list):
            next_matchups_data = []
    except SleeperError:
        next_matchups_data = []

    players_data = _get(f"{SLEEPER_BASE}players/nfl")

    # Trending adds/drops (best-effort)
    try:
        trending_adds = _get(f"{SLEEPER_BASE}players/nfl/trending/add")
    except SleeperError:
        trending_adds = []
    try:
        trending_drops = _get(f"{SLEEPER_BASE}players/nfl/trending/drop")
    except SleeperError:
        trending_drops = []

    player_id_to_name = {
        p_id: p_data.get("full_name")
        for p_id, p_data in players_data.items()
        if isinstance(p_data, dict) and p_data.get("full_name")
    }

    player_id_to_injury_info = {
        p_id: p_data
        for p_id, p_data in players_data.items()
        if isinstance(p_data, dict)
        and p_data.get("injury_status") not in (None, "Active")
    }

    return {
        "league_details": league_data,
        "rosters": rosters_data,
        "users": users_data,
        "matchups": matchups_data,
        "next_matchups": next_matchups_data,
        "players": players_data,
        "player_id_to_name": player_id_to_name,
        "player_id_to_injury_info": player_id_to_injury_info,
        "trending_adds": trending_adds if isinstance(trending_adds, list) else [],
        "trending_drops": trending_drops if isinstance(trending_drops, list) else [],
    }


def _group_matchups(matchups: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    groups: Dict[int, List[Dict[str, Any]]] = {}
    for m in matchups or []:
        mid = m.get("matchup_id")
        if mid is None:
            continue
        groups.setdefault(mid, []).append(m)
    return groups


def generate_report_script(data: Dict[str, Any], week: int) -> str:
    """Keep your spicy on-air script generator (zero avatar refs)."""
    if not data or not data.get("matchups") or not data.get("users") or not data.get("rosters") or not data.get("players"):
        return "Could not generate report due to missing data."

    report_lines = [f"Welcome back, fantasy fanatics! Week {week} is in the books—let’s dive in.\n"]

    league_name = (data.get("league_details") or {}).get("name") or "Your Fantasy League"
    users = data.get("users", [])
    rosters = data.get("rosters", [])
    players = data.get("players", {})

    user_map = {u.get("user_id"): u.get("display_name", f"User {u.get('user_id')}") for u in users}
    roster_to_user = {r.get("roster_id"): r.get("owner_id") for r in rosters}
    player_id_to_name = {pid: p.get("full_name") for pid, p in players.items() if isinstance(p, dict) and p.get("full_name")}
    player_id_to_injury_info = {
        pid: p for pid, p in players.items()
        if isinstance(p, dict) and p.get("injury_status") not in (None, "Active")
    }

    blowout_phrases_score = [
        "  That’s a {score_diff:.2f}-point beatdown.\n",
        "  A monumental {score_diff:.2f}-point victory!\n",
        "  A {score_diff:.2f}-point shellacking!\n",
    ]
    nailbiter_phrases = [
        "  Phew! That was close.\n",
        "  A real cliffhanger!\n",
    ]

    for matchup_id, teams in _group_matchups(data["matchups"]).items():
        if len(teams) != 2:
            continue
        t1, t2 = teams
        t1_owner = roster_to_user.get(t1.get("roster_id"))
        t2_owner = roster_to_user.get(t2.get("roster_id"))
        t1_name = user_map.get(t1_owner, f"Unknown {t1_owner}")
        t2_name = user_map.get(t2_owner, f"Unknown {t2_owner}")

        p1 = float(t1.get("points", 0))
        p2 = float(t2.get("points", 0))
        diff = abs(p1 - p2)
        winner = t1_name if p1 >= p2 else t2_name

        report_lines.append(f"\nMatchup {matchup_id}:\n")
        report_lines.append(f"  {t1_name} put up {p1:.2f} vs {t2_name}'s {p2:.2f}.\n")

        if diff >= 30:
            report_lines.append(random.choice(blowout_phrases_score).format(score_diff=diff))
        elif diff <= 5:
            report_lines.append(random.choice(nailbiter_phrases))
        else:
            report_lines.append(f"  A solid win for {winner}.\n")

        starters = t1.get("starters") if p1 >= p2 else t2.get("starters")
        if starters:
            highlight = random.choice(starters)
            name = player_id_to_name.get(highlight, "a mysterious superstar")
            report_lines.append(f"  🔥 Projection Obliterator: {name}.\n")

    report_lines.append("\n--- Injury Report ---\n")
    notable = list(player_id_to_injury_info.values())[:5]
    if notable:
        for info in notable:
            report_lines.append(
                f"  {info.get('full_name','Player')} — {info.get('injury_status','Questionable')} "
                f"({info.get('injury_body_part','undisclosed')}).\n"
            )
        extra = max(0, len(player_id_to_injury_info) - 5)
        if extra:
            report_lines.append(f"  ...and {extra} more nursing various ailments.\n")
    else:
        report_lines.append("  No significant injuries reported.\n")

    if data.get("next_matchups"):
        report_lines.append(f"\n--- Looking Ahead: Week {week + 1} Preview ---\n")
        previewed = 0
        for mid, teams in _group_matchups(data["next_matchups"]).items():
            if previewed >= 3 or len(teams) != 2:
                continue
            a, b = teams
            a_name = user_map.get(roster_to_user.get(a.get("roster_id")), "Unknown")
            b_name = user_map.get(roster_to_user.get(b.get("roster_id")), "Unknown")
            report_lines.append(f"  {a_name} vs {b_name}\n")
            previewed += 1

    if data.get("trending_adds") or data.get("trending_drops"):
        report_lines.append("\n--- Waiver Wire Watch ---\n")
    if data.get("trending_adds"):
        adds = [data["player_id_to_name"].get(x.get("player_id")) for x in data["trending_adds"][:3] if x.get("player_id")]
        adds = [a for a in adds if a]
        if adds:
            report_lines.append(f"  Hot Pickups: {', '.join(adds)}\n")
    if data.get("trending_drops"):
        drops = [data["player_id_to_name"].get(x.get("player_id")) for x in data["trending_drops"][:3] if x.get("player_id")]
        drops = [d for d in drops if d]
        if drops:
            report_lines.append(f"  Falling Stars: {', '.join(drops)}\n")

    report_lines.append(f"\nThat’s your Week {week} wrap-up from {league_name}.\n")
    return "".join(report_lines)


def generate_json_report(data: Dict[str, Any], week: int) -> Dict[str, Any]:
    """Structured JSON with matchups, injuries, next week, and trends."""
    league_name = (data.get("league_details") or {}).get("name") or "Unknown League"
    users = data.get("users", [])
    rosters = data.get("rosters", [])
    player_id_to_name = data.get("player_id_to_name", {})
    player_id_to_injury_info = data.get("player_id_to_injury_info", {})

    user_map = {u.get("user_id"): u.get("display_name", f"User {u.get('user_id')}") for u in users}
    roster_to_user = {r.get("roster_id"): r.get("owner_id") for r in rosters}

    out: Dict[str, Any] = {
        "report_metadata": {
            "league_name": league_name,
            "week": week,
            "generated_timestamp": datetime.now(timezone.utc).isoformat(),
            "report_type": "automated_json",
            "version": "enhanced_v4_no_avatars",
        },
        "matchups": [],
        "injury_report": {"featured_injuries": [], "total_injured_players": len(player_id_to_injury_info)},
        "next_week_preview": {"week": week + 1, "matchups": []},
        "waiver_wire_watch": {"hot_pickups": [], "falling_stars": []},
    }

    for mid, teams in _group_matchups(data.get("matchups", [])).items():
        if len(teams) != 2:
            continue
        t1, t2 = teams
        u1 = user_map.get(roster_to_user.get(t1.get("roster_id")), "Unknown")
        u2 = user_map.get(roster_to_user.get(t2.get("roster_id")), "Unknown")
        p1 = float(t1.get("points", 0))
        p2 = float(t2.get("points", 0))
        diff = abs(p1 - p2)
        out["matchups"].append({
            "matchup_id": mid,
            "team1": {"name": u1, "points": p1, "result": "win" if p1 > p2 else "loss"},
            "team2": {"name": u2, "points": p2, "result": "win" if p2 > p1 else "loss"},
            "point_difference": round(diff, 2),
            "matchup_type": "blowout" if diff > 30 else "close_game",
        })

    for info in list(player_id_to_injury_info.values())[:5]:
        out["injury_report"]["featured_injuries"].append({
            "player": info.get("full_name", "Unknown"),
            "status": info.get("injury_status", "Unknown"),
            "injury": info.get("injury_body_part", "Unknown"),
            "team": info.get("team", "FA"),
        })

    for mid, teams in _group_matchups(data.get("next_matchups", [])).items():
        if len(teams) != 2:
            continue
        a, b = teams
        a_name = user_map.get(roster_to_user.get(a.get("roster_id")), "Unknown")
        b_name = user_map.get(roster_to_user.get(b.get("roster_id")), "Unknown")
        out["next_week_preview"]["matchups"].append({"team1": a_name, "team2": b_name, "matchup_id": mid})

    for add in (data.get("trending_adds") or [])[:3]:
        pid = add.get("player_id")
        if pid and pid in player_id_to_name:
            out["waiver_wire_watch"]["hot_pickups"].append({"player": player_id_to_name[pid], "count": add.get("count", 0)})

    for drop in (data.get("trending_drops") or [])[:3]:
        pid = drop.get("player_id")
        if pid and pid in player_id_to_name:
            out["waiver_wire_watch"]["falling_stars"].append({"player": player_id_to_name[pid], "count": drop.get("count", 0)})

    return out


def current_nfl_week(today: datetime | None = None) -> int:
    """Approximate NFL regular-season week. Clamp to 1..18."""
    # 2025 Week 1 kickoff approx: Sep 4, 2025 (keep tunable)
    start = datetime(2025, 9, 4, tzinfo=timezone.utc)
    now = (today or datetime.now(timezone.utc)).astimezone(timezone.utc)
    days = (now - start).days
    wk = 1 if days < 0 else (days // 7) + 1
    return max(1, min(18, wk))
