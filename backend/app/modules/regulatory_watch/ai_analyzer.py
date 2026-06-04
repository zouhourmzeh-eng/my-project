import json
import logging
from app.services.ai import client, model_name, extract_json
from app.models import RegulatoryUpdate, Project

logger = logging.getLogger(__name__)

async def analyze_regulatory_impact(update: RegulatoryUpdate, project: Project) -> dict:
    """
    Analyzes a regulatory update to determine its impact on a specific project.
    Returns a dictionary containing:
    - is_impacted (bool)
    - impact_summary (str)
    - impacted_areas (list of str)
    - suggested_actions (list of str)
    """
    if not client:
        logger.warning("AI client not available. Simulation mode for impact analysis.")
        return {
            "is_impacted": True,
            "impact_summary": "Simulated impact due to AI being offline.",
            "impacted_areas": ["SOP-01", "Risk Management Plan"],
            "suggested_actions": ["Review FDA guidance", "Update Risk File"]
        }

    prompt = f"""
    En tant qu'Expert Senior en Affaires Réglementaires et Qualité (QMS), analyse l'impact de cette mise à jour réglementaire sur le projet suivant.

    MISE À JOUR RÉGLEMENTAIRE :
    - Titre : {update.title}
    - Résumé : {update.summary}
    - Gravité : {update.severity}

    PROJET :
    - Produit : {project.product}
    - Secteur : {project.activity_sector}
    - Marché : {project.market}
    - Normes applicables : {project.standards}

    Ta mission est d'évaluer si et comment cette mise à jour impacte le projet.
    Réponds EXCLUSIVEMENT au format JSON strict avec les clés suivantes :
    - "is_impacted": booléen (true si le projet est concerné, false sinon)
    - "impact_summary": chaîne de caractères (résumé de l'impact en 1-2 phrases)
    - "impact_justification": chaîne de caractères (explication détaillée de *pourquoi* ce projet est impacté, même si aucune norme officielle n'est modifiée - ex: produit similaire, état de l'art, surveillance post-marché)
    - "standards_updated": liste de chaînes (ex: ["ISO 13485:2016", "MDR 2017/745"])
    - "procedures_impacted": liste d'objets (chaque objet doit avoir "procedure_name" et "changes_needed")
    - "suggested_actions": liste de chaînes (actions générales)
    - "capa_recommendations": liste de chaînes (recommandations spécifiques pour ouvrir une CAPA, ex: "Ouvrir une CAPA pour analyser les défauts potentiels sur notre composant Y")

    Exemple de sortie JSON :
    {{
        "is_impacted": true,
        "impact_summary": "La nouvelle directive FDA modifie les exigences de cybersécurité pour les dispositifs connectés.",
        "impact_justification": "Même sans changement de norme, la FDA souligne une vulnérabilité sur un composant similaire à celui utilisé dans notre projet. Par conséquent, la surveillance post-marché exige une réévaluation de nos risques.",
        "standards_updated": ["FDA Cybersecurity Guidance 2023"],
        "procedures_impacted": [
            {{"procedure_name": "SOP-04 Cybersécurité", "changes_needed": "Ajouter la gestion des vulnérabilités post-marché"}},
            {{"procedure_name": "SOP-01 Analyse de risques", "changes_needed": "Inclure les vecteurs d'attaque réseau"}}
        ],
        "suggested_actions": ["Réviser l'analyse de risques cyber", "Mettre à jour l'architecture logicielle"],
        "capa_recommendations": ["Initier une CAPA pour vérifier si notre logiciel actuel est vulnérable à la faille identifiée par la FDA"]
    }}
    Ne renvoie aucun texte en dehors du JSON.
    """

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "Tu es un assistant JSON strict. Tu réponds uniquement en JSON valide."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={ "type": "json_object" } # Using JSON mode if supported
        )
        content = response.choices[0].message.content
        result = json.loads(content)
        
        # Ensure default keys
        return {
            "is_impacted": result.get("is_impacted", False),
            "impact_summary": result.get("impact_summary", ""),
            "impact_justification": result.get("impact_justification", ""),
            "standards_updated": result.get("standards_updated", []),
            "procedures_impacted": result.get("procedures_impacted", []),
            "suggested_actions": result.get("suggested_actions", []),
            "capa_recommendations": result.get("capa_recommendations", [])
        }
        
    except Exception as e:
        logger.error(f"Error analyzing impact: {str(e)}")
        return {
            "is_impacted": False,
            "impact_summary": f"Erreur d'analyse IA : {str(e)}",
            "impacted_areas": [],
            "suggested_actions": []
        }
