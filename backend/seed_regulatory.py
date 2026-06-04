import asyncio
from sqlalchemy import select
from app.db.base import AsyncSessionLocal
from app.models import RegulatorySource, RegulatorySourceType

async def seed_sources():
    sources = [
        {
            "name": "FDA MedWatch Safety Alerts",
            "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/medwatch/rss.xml",
            "source_type": RegulatorySourceType.rss,
            "parser_name": "fda_rss",
            "frequency_hours": 24
        },
        {
            "name": "FDA Recalls & Safety",
            "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/recalls-and-safety-alerts/rss.xml",
            "source_type": RegulatorySourceType.rss,
            "parser_name": "fda_rss",
            "frequency_hours": 24
        },
        {
            "name": "EU MDCG Guidance Documents",
            "url": "https://ec.europa.eu/health/system/files/rss/md_guidance_documents_en.xml",
            "source_type": RegulatorySourceType.rss,
            "parser_name": "eu_rss",
            "frequency_hours": 24
        }
    ]

    async with AsyncSessionLocal() as session:
        for s_data in sources:
            result = await session.execute(
                select(RegulatorySource).where(RegulatorySource.url == s_data["url"])
            )
            if not result.scalar_one_or_none():
                source = RegulatorySource(**s_data)
                session.add(source)
                print(f"Added source: {s_data['name']}")
        
        await session.commit()

if __name__ == "__main__":
    asyncio.run(seed_sources())
