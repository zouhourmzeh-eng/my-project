import json
import logging
from typing import List, Dict, Any
from app.services.ai import client, extract_json

logger = logging.getLogger(__name__)

async def analyze_gap_for_documents(project: Any, documents_data: List[Dict[str, str]], target_standards: str) -> List[Dict[str, Any]]:
    """
    Analyzes the gap between a project's SMQ documents and target standards.
    
    project: Project model instance
    documents_data: List of dicts containing 'title', 'description', and 'content' (extracted PDF text)
    target_standards: The specific standard(s) to check against
    
    Returns a list of dicts with gaps, suggestions, and CAPAs.
    """
    if not client:
        logger.warning("AI client not available for gap analysis.")
        return []

    docs_context = ""
    for idx, doc in enumerate(documents_data, 1):
        docs_context += f"--- Document {idx}: {doc['title']} ---\n"
        docs_context += f"Description: {doc['description']}\n"
        # Truncate content to avoid token limits if it's too long (e.g. max 15000 chars per doc)
        content_trunc = doc['content'][:15000] + ("..." if len(doc['content']) > 15000 else "")
        docs_context += f"Extracted Text:\n{content_trunc}\n\n"

    system_prompt = f"""Tu es un Lead Auditeur Qualité de classe mondiale, expert en affaires réglementaires et systèmes de management de la qualité (SMQ).
Ton rôle est de réaliser une Analyse de Gap (Gap Analysis) exhaustive et extrêmement rigoureuse des documents SMQ fournis par rapport aux exigences de la/des norme(s) suivante(s) : {target_standards}.

CONTEXTE DU PROJET :
- Entreprise : {project.company_name}
- Secteur d'activité : {project.activity_sector}
- Produit concerné : {project.product}
- Marché cible : {project.market}

DOCUMENTS SMQ À ANALYSER :
{docs_context}

INSTRUCTIONS DE CONFORMITÉ :
Pour chaque document fourni :
1. Analyse son adéquation par rapport aux clauses spécifiques de la norme {target_standards}.
2. Identifie de manière chirurgicale chaque écart (manque de procédure, d'enregistrement, de rôle défini, etc.).
3. Calcule le score de conformité ("compliance_score") selon la grille suivante :
   - 100% : Parfaitement conforme, aucune action requise.
   - 80-99% : Conforme globalement, mais nécessite des ajustements mineurs ou clarifications.
   - 50-79% : Non conforme, des sections importantes de la norme ou exigences clés sont absentes.
   - 0-49% : Document largement incomplet ou hors-sujet.

4. Pour chaque écart identifié, suggère des recommandations de mise à jour concrètes et génère des CAPA (Actions Correctives et Préventives) actionnables.

Tu dois STRICTEMENT ET UNIQUEMENT renvoyer un tableau JSON valide. N'ajoute aucun texte de présentation ou d'introduction avant ou après.

Format JSON attendu :
[
  {{
    "document_title": "Titre exact du document",
    "compliance_score": 75,
    "compliance_status": "Non conforme",
    "missing_clauses": [
      "Clause X.X.X - Titre de la clause (ISO XXXX:XXXX)"
    ],
    "update_suggestions": "Instructions pas-à-pas détaillant les sections à ajouter ou à modifier dans le document.",
    "capas": [
      {{
        "title": "Nom de l'action corrective (ex: Mettre à jour la procédure de maîtrise des risques)",
        "description": "Description détaillée des étapes nécessaires pour combler cet écart spécifique (responsable suggéré, données à collecter)."
      }}
    ]
  }}
]

RÈGLES D'OR :
- Sois extrêmement précis dans les citations de normes (ex: Clause 7.3.3 de l'ISO 13485:2016).
- Si le document est 100% conforme, "missing_clauses" doit être une liste vide [], "capas" doit être une liste vide [], et "update_suggestions" doit encourager l'équipe avec un message de conformité.
- "compliance_score" doit être un nombre entier de 0 à 100 indiquant le pourcentage estimé de conformité.
- "compliance_status" doit être "Conforme" (si score >= 80) ou "Non conforme" (si score < 80).
- Le retour DOIT être du JSON valide.
"""

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Analyse les documents ci-dessus par rapport aux normes et renvoie le rapport au format JSON."}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        content = response.choices[0].message.content
        logger.info(f"Gap Analysis LLM Response: {content[:200]}...")
        
        parsed_json = extract_json(content)
        if isinstance(parsed_json, list):
            return parsed_json
        else:
            logger.error("JSON returned by LLM is not a list.")
            return []
            
    except Exception as e:
        logger.error(f"Error during AI gap analysis: {e}")
        return []
