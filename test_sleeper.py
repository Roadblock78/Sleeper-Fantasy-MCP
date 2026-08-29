import asyncio
import httpx

USER_ID = "982607912881209344"

async def main():
    async with httpx.AsyncClient(timeout=20) as client:
        user = (await client.get(f"https://api.sleeper.app/v1/user/{USER_ID}"))
        user.raise_for_status()
        print("User:", user.json())

        leagues = (await client.get(
            f"https://api.sleeper.app/v1/user/{USER_ID}/leagues/nfl/2026"
        ))
        leagues.raise_for_status()
        print("\n2026 leagues:")
        for league in leagues.json():
            print("-", league.get("name"), league.get("league_id"))

if __name__ == "__main__":
    asyncio.run(main())
