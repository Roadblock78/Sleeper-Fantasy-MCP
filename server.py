import os
import time
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

SLEEPER_BASE = "https://api.sleeper.app/v1"
DEFAULT_USER_ID = os.getenv("SLEEPER_USER_ID", "982607912881209344")
DEFAULT_SEASON = os.getenv("SLEEPER_SEASON", "2026")
REQUEST_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))

mcp = FastMCP(
    "Sleeper Fantasy NFL",
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    ),
    instructions=(
        "Read-only access to Sleeper NFL fantasy data. "
        "Default user_id is the owner's configured Sleeper account. "
        "Use get_my_leagues first when the league is not yet known, then use the "
        "returned league_id with roster, matchup, transaction and draft tools."
    ),
)

_players_cache: dict[str, Any] = {"loaded_at": 0.0, "data": None}
PLAYERS_CACHE_SECONDS = 6 * 60 * 60


async def sleeper_get(path: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{SLEEPER_BASE}{path}"
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def get_players_db() -> dict[str, Any]:
    now = time.time()
    cached = _players_cache["data"]
    if cached is not None and now - _players_cache["loaded_at"] < PLAYERS_CACHE_SECONDS:
        return cached

    data = await sleeper_get("/players/nfl")
    _players_cache["data"] = data
    _players_cache["loaded_at"] = now
    return data


@mcp.tool()
async def get_my_sleeper_user() -> dict[str, Any]:
    """Get the configured Sleeper user's public profile."""
    return await sleeper_get(f"/user/{DEFAULT_USER_ID}")


@mcp.tool()
async def get_my_leagues(season: str = DEFAULT_SEASON) -> list[dict[str, Any]]:
    """Get all NFL Sleeper leagues for the configured user in a season."""
    return await sleeper_get(f"/user/{DEFAULT_USER_ID}/leagues/nfl/{season}")


@mcp.tool()
async def get_league(league_id: str) -> dict[str, Any]:
    """Get league name, scoring/settings, roster positions and status."""
    return await sleeper_get(f"/league/{league_id}")


@mcp.tool()
async def get_league_users(league_id: str) -> list[dict[str, Any]]:
    """Get the users/managers in a Sleeper league."""
    return await sleeper_get(f"/league/{league_id}/users")


@mcp.tool()
async def get_league_rosters(league_id: str) -> list[dict[str, Any]]:
    """Get all rosters in a league, including starters, players and roster settings."""
    return await sleeper_get(f"/league/{league_id}/rosters")


@mcp.tool()
async def get_my_roster(league_id: str) -> dict[str, Any]:
    """Get only the configured user's roster in a league."""
    rosters = await sleeper_get(f"/league/{league_id}/rosters")
    for roster in rosters:
        if str(roster.get("owner_id")) == str(DEFAULT_USER_ID):
            return roster
    return {
        "error": "Configured user does not own a roster in this league.",
        "user_id": DEFAULT_USER_ID,
        "league_id": league_id,
    }


@mcp.tool()
async def get_week_matchups(league_id: str, week: int) -> list[dict[str, Any]]:
    """Get every matchup and roster score for a given NFL fantasy week."""
    return await sleeper_get(f"/league/{league_id}/matchups/{week}")


@mcp.tool()
async def get_week_transactions(
    league_id: str,
    week: int,
) -> list[dict[str, Any]]:
    """Get waiver claims, free-agent moves and trades for a league week."""
    return await sleeper_get(f"/league/{league_id}/transactions/{week}")


@mcp.tool()
async def get_league_drafts(league_id: str) -> list[dict[str, Any]]:
    """Get drafts associated with a league."""
    return await sleeper_get(f"/league/{league_id}/drafts")


@mcp.tool()
async def get_draft_picks(draft_id: str) -> list[dict[str, Any]]:
    """Get all picks from a specific Sleeper draft."""
    return await sleeper_get(f"/draft/{draft_id}/picks")


@mcp.tool()
async def get_traded_picks(league_id: str) -> list[dict[str, Any]]:
    """Get traded future draft picks for a league."""
    return await sleeper_get(f"/league/{league_id}/traded_picks")


@mcp.tool()
async def get_trending_players(
    trend_type: str = "add",
    lookback_hours: int = 24,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """
    Get Sleeper's trending NFL adds or drops.
    trend_type must be 'add' or 'drop'.
    """
    trend_type = trend_type.lower().strip()
    if trend_type not in {"add", "drop"}:
        return [{"error": "trend_type must be 'add' or 'drop'"}]
    return await sleeper_get(
        f"/players/nfl/trending/{trend_type}",
        params={"lookback_hours": lookback_hours, "limit": limit},
    )


@mcp.tool()
async def search_players(
    query: str,
    position: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Search Sleeper's NFL player database by name.
    Optionally filter by position such as QB, RB, WR, TE, K or DEF.
    """
    q = query.casefold().strip()
    pos = position.upper().strip() if position else None
    players = await get_players_db()

    results: list[dict[str, Any]] = []
    for player_id, p in players.items():
        if not isinstance(p, dict):
            continue

        full_name = (
            p.get("full_name")
            or " ".join(
                x for x in [p.get("first_name"), p.get("last_name")] if x
            )
        )
        haystack = " ".join(
            str(x)
            for x in [
                full_name,
                p.get("first_name"),
                p.get("last_name"),
                p.get("team"),
                p.get("position"),
            ]
            if x
        ).casefold()

        if q not in haystack:
            continue
        if pos and str(p.get("position", "")).upper() != pos:
            continue

        results.append(
            {
                "player_id": player_id,
                "full_name": full_name,
                "position": p.get("position"),
                "team": p.get("team"),
                "status": p.get("status"),
                "injury_status": p.get("injury_status"),
                "years_exp": p.get("years_exp"),
                "age": p.get("age"),
            }
        )
        if len(results) >= max(1, min(limit, 100)):
            break

    return results


@mcp.tool()
async def get_players_by_id(player_ids: list[str]) -> list[dict[str, Any]]:
    """Resolve Sleeper player IDs to names, teams, positions and injury status."""
    players = await get_players_db()
    result = []
    for player_id in player_ids[:250]:
        p = players.get(str(player_id), {})
        result.append(
            {
                "player_id": str(player_id),
                "full_name": p.get("full_name"),
                "first_name": p.get("first_name"),
                "last_name": p.get("last_name"),
                "position": p.get("position"),
                "team": p.get("team"),
                "status": p.get("status"),
                "injury_status": p.get("injury_status"),
            }
        )
    return result


@mcp.tool()
async def get_league_snapshot(league_id: str) -> dict[str, Any]:
    """
    Get a compact league overview containing league settings, managers and rosters.
    Useful as the first call when analysing a known league.
    """
    league = await sleeper_get(f"/league/{league_id}")
    users = await sleeper_get(f"/league/{league_id}/users")
    rosters = await sleeper_get(f"/league/{league_id}/rosters")

    user_map = {str(u.get("user_id")): u for u in users}
    compact_rosters = []
    for r in rosters:
        owner_id = str(r.get("owner_id")) if r.get("owner_id") is not None else None
        manager = user_map.get(owner_id, {})
        compact_rosters.append(
            {
                "roster_id": r.get("roster_id"),
                "owner_id": r.get("owner_id"),
                "manager": manager.get("display_name") or manager.get("username"),
                "is_me": owner_id == str(DEFAULT_USER_ID),
                "starters": r.get("starters"),
                "players": r.get("players"),
                "reserve": r.get("reserve"),
                "taxi": r.get("taxi"),
                "settings": r.get("settings"),
            }
        )

    return {
        "league": {
            "league_id": league.get("league_id"),
            "name": league.get("name"),
            "season": league.get("season"),
            "status": league.get("status"),
            "total_rosters": league.get("total_rosters"),
            "roster_positions": league.get("roster_positions"),
            "scoring_settings": league.get("scoring_settings"),
            "settings": league.get("settings"),
        },
        "rosters": compact_rosters,
    }


if __name__ == "__main__":
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = int(os.getenv("PORT", "8000"))
    mcp.run(transport="streamable-http")
