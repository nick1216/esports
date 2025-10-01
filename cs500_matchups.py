import asyncio
from scraper import CS500Scraper

cs500_scraper = CS500Scraper()

async def main():
    await cs500_scraper.get_matchids()

if __name__ == "__main__":
    asyncio.run(main())