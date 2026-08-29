# Sleeper Fantasy MCP

A small read-only MCP server that exposes Sleeper NFL fantasy data to an MCP client such as ChatGPT.

Configured Sleeper account:

- Username: `roadblock78`
- Sleeper user ID: `982607912881209344`
- Default season: `2026`

No Sleeper password or API key is required. The server only performs GET requests against Sleeper's public API.

## What it can read

The MCP tools include:

- your Sleeper profile
- your leagues for a season
- league settings and scoring
- all league managers and rosters
- your own roster
- weekly matchups
- weekly transactions, waivers and trades
- league drafts and draft picks
- traded picks
- Sleeper trending adds/drops
- player search and player-ID resolution
- a combined league snapshot

It cannot set a lineup, submit a waiver, make a trade or otherwise modify Sleeper.

## 1. Test locally

You need Python 3.10+.

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python server.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

The MCP endpoint will normally be:

```text
http://127.0.0.1:8000/mcp
```

You can inspect it with the MCP Inspector:

```bash
npx -y @modelcontextprotocol/inspector
```

Then connect the Inspector to:

```text
http://127.0.0.1:8000/mcp
```

Try `get_my_sleeper_user` and `get_my_leagues`.

## 2. Deploy it

ChatGPT requires a remotely reachable MCP server. A localhost-only server cannot be connected directly.

This project includes a Dockerfile and `render.yaml`, so one simple route is:

1. Create a GitHub repository.
2. Upload these project files.
3. Sign in to Render.
4. Create a new Blueprint/Web Service from the GitHub repository.
5. Render should detect `render.yaml` / the Dockerfile.
6. Deploy.
7. Your MCP address should be similar to:

```text
https://YOUR-SERVICE.onrender.com/mcp
```

The server is read-only and does not require authentication. Because it is public, do not add tools that expose private systems or secrets without adding authentication first.

Other Docker-compatible hosts such as Railway, Fly.io, Azure Container Apps, Google Cloud Run or AWS can also host it.

## 3. Connect it to ChatGPT

Current ChatGPT support depends on plan/workspace.

In ChatGPT Developer Mode / custom app settings:

1. Create a custom MCP app.
2. Enter the deployed MCP endpoint:
   `https://YOUR-SERVICE.onrender.com/mcp`
3. Use no authentication for this personal read-only version.
4. Scan tools.
5. Enable the app.

Once connected, prompts can be as simple as:

- "Sleeper: show me my 2026 leagues."
- "Analyse my roster."
- "How does my matchup look this week?"
- "Who are my weakest starters?"
- "What waiver positions should I prioritise?"
- "Show the most-added players on Sleeper and tell me which are relevant to my roster."
- "Review this week's league transactions."

## Tool usage pattern

When a conversation does not yet know the league ID:

1. `get_my_leagues`
2. choose the intended league
3. `get_league_snapshot`
4. `get_week_matchups` for the requested week
5. resolve relevant player IDs with `get_players_by_id`

This avoids repeatedly copying JSON into ChatGPT.

## Updating the season

Set the environment variable:

```text
SLEEPER_SEASON=2027
```

or pass the season to `get_my_leagues`.

## Security note

Sleeper's public API exposes public fantasy-league information. This server contains your Sleeper user ID, which is not a password or authentication credential. Nevertheless, anyone who can reach a completely unauthenticated MCP endpoint can invoke its tools.

For a personal deployment, use an obscure deployment URL or add authentication at the hosting/proxy layer if desired.
