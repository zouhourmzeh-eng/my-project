import asyncio
import logging
import sys
from sqlalchemy import select, func
from app.db.base import AsyncSessionLocal
from app.models import RegulatoryUpdate, RegulatoryImpact, RegulatorySource, Project
from app.modules.regulatory_watch.workers import fetch_regulatory_updates

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def check():
    print("--- DÉBUT DE LA RÉCUPÉRATION MANUELLE ---")
    await fetch_regulatory_updates()
    print("--- FIN DE LA RÉCUPÉRATION MANUELLE ---\n")

    async with AsyncSessionLocal() as session:
        # Check Sources
        sources = await session.execute(select(RegulatorySource))
        sources_list = sources.scalars().all()
        
        # Check Updates
        updates = await session.execute(select(RegulatoryUpdate).order_by(RegulatoryUpdate.publication_date.desc()).limit(5))
        updates_list = updates.scalars().all()
        
        # Check Impacts
        impacts = await session.execute(select(RegulatoryImpact).limit(5))
        impacts_list = impacts.scalars().all()

        # Check Projects
        projects = await session.execute(select(Project))
        projects_count = len(projects.scalars().all())
        
        print("=== RAPPORT D'ÉTAT RÉEL ===")
        print(f"Sources actives : {len(sources_list)}")
        for s in sources_list:
            print(f"  - {s.name}: {s.url}")
            
        print(f"\nProjets en base : {projects_count}")
        print(f"Mises à jour capturées : {len(updates_list)}")
        print(f"Analyses d'impact générées : {len(impacts_list)}")
        
        if updates_list:
            print("\nDernières mises à jour :")
            for u in updates_list:
                print(f"- [{u.severity}] {u.title}")
        else:
            print("\n!!! AUCUNE MISE À JOUR TROUVÉE !!! Vérifiez si les URLs RSS sont accessibles.")

        if impacts_list:
            print("\nDernières analyses d'impact :")
            for i in impacts_list:
                print(f"- Impact sur Projet ID {i.project_id}: {i.impact_summary[:100]}...")
        
        print("============================\n")

if __name__ == "__main__":
    asyncio.run(check())
