import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.models import RegulatorySource, RegulatoryUpdate, SeverityLevel
from app.modules.regulatory_watch.parsers.fda_parser import FdaRssParser
from app.modules.regulatory_watch.parsers.eu_parser import EuRegulatoryParser

logger = logging.getLogger(__name__)

PARSERS = {
    "fda_rss": FdaRssParser(),
    "eu_rss": EuRegulatoryParser()
}

async def fetch_regulatory_updates():
    """Background job to fetch updates from all active regulatory sources."""
    logger.info("Starting regulatory updates fetch job...")
    async with AsyncSessionLocal() as session:
        # Get active sources
        result = await session.execute(
            select(RegulatorySource).where(RegulatorySource.is_active == True)
        )
        sources = result.scalars().all()
        
        for source in sources:
            logger.info(f"Fetching from source: {source.name} ({source.url})")
            parser = PARSERS.get(source.parser_name)
            
            if not parser:
                logger.error(f"Parser '{source.parser_name}' not found for source '{source.name}'")
                continue
            
            try:
                updates_data = await parser.parse(source.url)
                new_updates = []
                
                for update_data in updates_data:
                    # Check if update already exists (by URL or title)
                    # For simplicity, let's use original_url
                    existing = await session.execute(
                        select(RegulatoryUpdate)
                        .where(RegulatoryUpdate.original_url == update_data["original_url"])
                    )
                    if existing.scalar_one_or_none():
                        continue
                    
                    severity_enum = SeverityLevel.medium
                    if update_data["severity"] == "high":
                        severity_enum = SeverityLevel.high
                    elif update_data["severity"] == "low":
                        severity_enum = SeverityLevel.low
                    elif update_data["severity"] == "critical":
                        severity_enum = SeverityLevel.critical
                        
                    new_update = RegulatoryUpdate(
                        source_id=source.id,
                        title=update_data["title"],
                        publication_date=update_data.get("publication_date", datetime.utcnow()),
                        original_url=update_data["original_url"],
                        summary=update_data.get("summary", ""),
                        severity=severity_enum
                    )
                    session.add(new_update)
                    new_updates.append(new_update)
                
                if len(new_updates) > 0:
                    await session.commit()
                    logger.info(f"Added {len(new_updates)} new updates from {source.name}.")
                    
                    # Phase 3: AI Pipeline Integration
                    # Get all validated projects (or projects in progress)
                    from app.models import Project, RegulatoryImpact
                    from app.modules.regulatory_watch.ai_analyzer import analyze_regulatory_impact
                    import json
                    
                    projects_result = await session.execute(select(Project))
                    projects = projects_result.scalars().all()
                    
                    for update in new_updates:
                        for project in projects:
                            logger.info(f"Analyzing impact of '{update.title}' on project '{project.company_name}'")
                            impact_result = await analyze_regulatory_impact(update, project)
                            
                            if impact_result.get("is_impacted"):
                                # Create RegulatoryImpact record
                                impact = RegulatoryImpact(
                                    update_id=update.id,
                                    project_id=project.id,
                                    impact_summary=impact_result.get("impact_summary", ""),
                                    impact_justification=impact_result.get("impact_justification", ""),
                                    standards_updated=json.dumps(impact_result.get("standards_updated", [])),
                                    procedures_impacted=json.dumps(impact_result.get("procedures_impacted", [])),
                                    suggested_actions=json.dumps(impact_result.get("suggested_actions", [])),
                                    capa_recommendations=json.dumps(impact_result.get("capa_recommendations", []))
                                )
                                session.add(impact)
                                
                                # Trigger Notification for the consultant (project owner)
                                from app.services.notifications import notify_user
                                await notify_user(
                                    session,
                                    user_id=project.owner_id,
                                    title=f"⚠️ Regulatory Alert: {project.company_name}",
                                    body=f"New regulatory update detected: {update.title}",
                                    link="/regulatory-watch"
                                )
                    
                    await session.commit()
                    
            except Exception as e:
                logger.error(f"Error fetching source {source.name}: {e}")

scheduler = AsyncIOScheduler()

def start_scheduler():
    """Initializes and starts the background scheduler."""
    # Run fetch every 4 hours for MVP
    scheduler.add_job(fetch_regulatory_updates, 'interval', hours=4, id="fetch_regulatory_updates")
    scheduler.start()
    logger.info("Regulatory Watch Scheduler started.")
