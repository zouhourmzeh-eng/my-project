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

    system_prompt = f"""Tu es un Lead Auditeur Qualité de classe mondiale, expert en affaires réglementaires.
Ton rôle est de réaliser une Analyse de Gap (Gap Analysis) rigoureuse des documents SMQ fournis par rapport aux normes suivantes : {target_standards}.

CONTEXTE DU PROJET :
- Entreprise: {project.company_name}
- Secteur: {project.activity_sector}
- Produit: {project.product}
- Marché: {project.market}

DOCUMENTS FOURNIS :
{docs_context}

INSTRUCTIONS :
Pour chaque document fourni, analyse son contenu et détermine s'il répond aux exigences des normes ciblées.
S'il y a des écarts (gaps), tu dois les identifier clairement.
Tu dois renvoyer STRICTEMENT ET UNIQUEMENT un tableau JSON. Aucun texte avant ou après.

Format JSON attendu :
[
  {{
    "document_title": "Titre du document",
    "compliance_score": 75,
    "compliance_status": "Non conforme",
    "missing_clauses": ["Liste", "des", "clauses spécifiques manquantes", "ex: Clause 7.1.2 de l'ISO 13485"],
    "update_suggestions": "Explication détaillée de ce qu'il faut ajouter ou modifier dans le document pour être conforme.",
    "capas": [
      {{
        "title": "Titre court de l'action corrective",
        "description": "Description détaillée de l'action à mener pour combler cet écart."
      }}
    ]
  }}
]

RÈGLES :
- Si un document est parfaitement conforme et ne présente aucun écart, la note de conformité ("compliance_score") doit être de 100, le statut ("compliance_status") "Conforme", avec des listes vides ("missing_clauses": [], "capas": []) et un message positif dans "update_suggestions".
- "compliance_score" doit être un nombre entier de 0 à 100 indiquant le pourcentage estimé de conformité.
- "compliance_status" doit être "Conforme" (si score >= 80) ou "Non conforme" (si score < 80).
- Fais preuve d'une extrême précision. Cite les clauses spécifiques.
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
