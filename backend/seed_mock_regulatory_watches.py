import asyncio
import sys
import json
from datetime import datetime, timedelta
sys.path.append('.')

from app.db.base import AsyncSessionLocal
from app.models import (
    Project, RegulatorySource, RegulatorySourceType,
    RegulatoryUpdate, RegulatoryImpact, SeverityLevel
)
from app.models.models import RegulatoryImpactStatus
from sqlalchemy import select

async def seed_mock_watches():
    async with AsyncSessionLocal() as session:
        # Find active sources or create them
        res_sources = await session.execute(select(RegulatorySource))
        sources = res_sources.scalars().all()
        
        fda_source = None
        eu_source = None
        
        for s in sources:
            if "fda" in s.name.lower():
                fda_source = s
            elif "eu" in s.name.lower() or "europe" in s.name.lower():
                eu_source = s
                
        if not fda_source:
            fda_source = RegulatorySource(
                name="FDA MedWatch Safety Alerts",
                url="https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/medwatch/rss.xml",
                source_type=RegulatorySourceType.rss,
                parser_name="fda_rss",
                frequency_hours=24,
                is_active=True
            )
            session.add(fda_source)
            await session.flush()
            
        if not eu_source:
            eu_source = RegulatorySource(
                name="EU MDCG Guidance Documents",
                url="https://ec.europa.eu/health/system/files/rss/md_guidance_documents_en.xml",
                source_type=RegulatorySourceType.rss,
                parser_name="eu_rss",
                frequency_hours=24,
                is_active=True
            )
            session.add(eu_source)
            await session.flush()

        # Find all projects
        res_projects = await session.execute(select(Project))
        projects = res_projects.scalars().all()
        if not projects:
            print("No projects found to link regulatory impacts. Please create a project first.")
            return
            
        # Define mock updates
        mock_updates_data = [
            {
                "source_id": fda_source.id,
                "title": "Mise à jour FDA : Nouvelles directives sur la cybersécurité des dispositifs médicaux connectés (FDA-2026-N-1234)",
                "original_url": "https://www.fda.gov/medical-devices/safety-communications/fda-cybersecurity-guidance-2026",
                "summary": "La FDA a publié la version finale de son guide sur la cybersécurité des dispositifs médicaux connectés. Les fabricants doivent fournir un rapport détaillé des composants logiciels (Software Bill of Materials - SBOM) et des preuves de tests de pénétration rigoureux pour obtenir l'approbation de mise sur le marché.",
                "extracted_requirements": "1. Fourniture obligatoire d'un SBOM complet.\n2. Exigence de plans de remédiation des vulnérabilités sous 30 jours.\n3. Documentation systématique des tests d'intrusion.",
                "severity": SeverityLevel.critical,
                "publication_date": datetime.utcnow() - timedelta(days=2),
                "impacts": {
                    "impact_summary": "Cette réglementation impacte directement le logiciel de votre dispositif médical connecté. Vous devez réviser votre documentation de cybersécurité pour intégrer les exigences du SBOM et planifier des tests de pénétration.",
                    "impact_justification": "Le produit comporte des interfaces réseau et des communications sans fil pour la transmission des données de santé, ce qui le classe dans les cibles critiques visées par cette nouvelle directive de cybersécurité de la FDA.",
                    "standards_updated": ["Cybersecurity - IEC 62443-4-1:2018", "IEC 62304:2006/A1:2015"],
                    "procedures_impacted": [
                        {
                            "procedure_name": "SOP-04 : Développement Logiciel & Gestion de Configuration",
                            "changes_needed": "Intégrer la génération automatique du SBOM (Software Bill of Materials) à chaque version livrée."
                        },
                        {
                            "procedure_name": "SOP-09 : Gestion des Risques Sécurité",
                            "changes_needed": "Ajouter l'analyse systématique des menaces (Threat Modeling) et planifier des tests de pénétration annuels."
                        }
                    ],
                    "suggested_actions": [
                        "Générer le SBOM initial pour le logiciel en cours de développement",
                        "Mettre à jour le plan de gestion des risques avec les menaces réseau",
                        "Planifier un audit d'intrusion par un laboratoire externe certifié"
                    ],
                    "capa_recommendations": [
                        "CAPA-2026-CYBER: Mise en conformité de la cybersécurité selon la directive FDA 2026"
                    ],
                    "status": RegulatoryImpactStatus.pending
                }
            },
            {
                "source_id": fda_source.id,
                "title": "Alerte de sécurité FDA MedWatch : Risque de surchauffe des batteries de dispositifs médicaux portables",
                "original_url": "https://www.fda.gov/safety/medwatch-safety-alerts/battery-overheating-risk-medical-devices",
                "summary": "Des signalements de surchauffe excessive et de défaillance thermique sur des batteries lithium-ion utilisées dans des dispositifs connectés portables ont conduit à une mise en garde générale. La FDA recommande une réévaluation des circuits de charge et des dispositifs de coupure thermique.",
                "extracted_requirements": "1. Réévaluation des risques de dérive thermique.\n2. Contrôle de conformité de la gestion de charge selon la norme IEC 60601-1.",
                "severity": SeverityLevel.high,
                "publication_date": datetime.utcnow() - timedelta(days=5),
                "impacts": {
                    "impact_summary": "Impact élevé sur la conception matérielle et l'alimentation. Une réévaluation thermique complète des circuits de charge de la batterie est requise.",
                    "impact_justification": "Votre produit utilise une batterie rechargeable intégrée pour assurer sa portabilité. Cette alerte de sécurité exige une vérification immédiate des mécanismes de protection thermique.",
                    "standards_updated": ["IEC 60601-1:2014", "ISO 14971:2019"],
                    "procedures_impacted": [
                        {
                            "procedure_name": "SOP-05 : Conception Matérielle & Tests Électriques",
                            "changes_needed": "Vérifier les dispositifs de coupure en cas de surchauffe ou de surtension lors de la charge de la batterie."
                        },
                        {
                            "procedure_name": "SOP-08 : Gestion des Risques Matériels",
                            "changes_needed": "Mettre à jour l'analyse de risque FMEA (modes de défaillance) pour couvrir le cas de la surchauffe de la batterie."
                        }
                    ],
                    "suggested_actions": [
                        "Réaliser un test de montée en température en conditions limites d'utilisation",
                        "Demander le rapport de test IEC 62133 du fabricant de la batterie"
                    ],
                    "capa_recommendations": [
                        "CAPA-2026-TEMP: Revue de sécurité thermique de la batterie intégrée"
                    ],
                    "status": RegulatoryImpactStatus.in_review
                }
            },
            {
                "source_id": eu_source.id,
                "title": "Réglementation UE : Prolongation des périodes de transition MDR (UE) 2024/186",
                "original_url": "https://ec.europa.eu/health/md-sector/new-transition-periods-mdr-2024",
                "summary": "Le Parlement européen a officiellement approuvé une prolongation des périodes de transition pour certains dispositifs médicaux certifiés sous l'ancienne directive (MDD), à condition d'avoir entamé des démarches actives de certification MDR auprès d'un organisme notifié avant la fin de l'année 2025.",
                "extracted_requirements": "1. Notification formelle de transition d'ici fin 2025.\n2. Signature d'un contrat de transfert MDR d'ici mi-2026.",
                "severity": SeverityLevel.medium,
                "publication_date": datetime.utcnow() - timedelta(days=10),
                "impacts": {
                    "impact_summary": "Cette modification prolonge le délai autorisé pour finaliser votre dossier technique de marquage CE sous le règlement MDR (UE) 2017/745.",
                    "impact_justification": "Votre projet cible le marché européen et est actuellement en cours de transition vers la certification MDR. Cette prolongation vous permet de réajuster le calendrier de soumission sans rupture de marquage.",
                    "standards_updated": ["MDR (UE) 2017/745"],
                    "procedures_impacted": [
                        {
                            "procedure_name": "SOP-01 : Affaires Réglementaires & Stratégie de Marquage",
                            "changes_needed": "Mettre à jour le plan de transition réglementaire et notifier l'organisme notifié pour confirmer l'extension."
                        }
                    ],
                    "suggested_actions": [
                        "Contacter votre organisme notifié pour valider l'éligibilité de votre produit à l'extension",
                        "Ajuster le rétroplanning des audits de transition"
                    ],
                    "capa_recommendations": [],
                    "status": RegulatoryImpactStatus.addressed
                }
            }
        ]

        # Seed updates and impacts for each project
        for update_data in mock_updates_data:
            # Check if update already exists
            res_up = await session.execute(
                select(RegulatoryUpdate).where(RegulatoryUpdate.title == update_data["title"])
            )
            up = res_up.scalar_one_or_none()
            if not up:
                up = RegulatoryUpdate(
                    source_id=update_data["source_id"],
                    title=update_data["title"],
                    original_url=update_data["original_url"],
                    summary=update_data["summary"],
                    extracted_requirements=update_data["extracted_requirements"],
                    severity=update_data["severity"],
                    publication_date=update_data["publication_date"]
                )
                session.add(up)
                await session.flush()
                print(f"Created update: {up.title}")
            else:
                print(f"Update already exists: {up.title}")

            # For each project, create the impact
            for proj in projects:
                # Check if impact already exists for this project and update
                res_imp = await session.execute(
                    select(RegulatoryImpact).where(
                        RegulatoryImpact.update_id == up.id,
                        RegulatoryImpact.project_id == proj.id
                    )
                )
                imp = res_imp.scalar_one_or_none()
                if not imp:
                    imp_data = update_data["impacts"]
                    imp = RegulatoryImpact(
                        update_id=up.id,
                        project_id=proj.id,
                        impact_summary=imp_data["impact_summary"],
                        impact_justification=imp_data["impact_justification"],
                        standards_updated=json.dumps(imp_data["standards_updated"]),
                        procedures_impacted=json.dumps(imp_data["procedures_impacted"]),
                        suggested_actions=json.dumps(imp_data["suggested_actions"]),
                        capa_recommendations=json.dumps(imp_data["capa_recommendations"]),
                        status=imp_data["status"]
                    )
                    session.add(imp)
                    print(f"Created impact for project '{proj.company_name}' and update '{up.title}'")
                else:
                    print(f"Impact already exists for project '{proj.company_name}' and update '{up.title}'")

        await session.commit()
        print("Successfully seeded all mock regulatory updates and impacts!")

if __name__ == "__main__":
    asyncio.run(seed_mock_watches())
