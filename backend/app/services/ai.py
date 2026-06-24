import json
import re
import logging
from openai import AsyncOpenAI
from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = None
model_name = "gpt-3.5-turbo"

def init_client():
    global client, model_name
    if settings.OPENAI_API_KEY:
        if settings.OPENAI_API_KEY.startswith("gsk_"):
            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url="https://api.groq.com/openai/v1",
                timeout=30.0
            )
            model_name = "llama-3.3-70b-versatile"
            logger.info(f"AI Client initialized with Groq model: {model_name}")
        else:
            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=30.0
            )
            model_name = "gpt-3.5-turbo"
            logger.info(f"AI Client initialized with OpenAI model: {model_name}")
    else:
        logger.warning("OPENAI_API_KEY not found. AI features will run in simulation mode.")

init_client()

def get_smart_fallback_standards(project_data: dict) -> list[str]:
    """Generates customized, relevant standards based on project fields as a smart fallback."""
    sector = str(project_data.get('activity_sector', '')).lower()
    product = str(project_data.get('product', '')).lower()
    market = str(project_data.get('market', '')).upper()
    
    standards = []
    
    # Check for AI/Machine Learning
    is_ai = any(k in product or k in sector for k in ["ai", "ia", "intelligence", "learning", "ml", "deep", "neural", "générative", "generative", "model"])
    
    # 1. Base QMS standard based on Sector
    if any(k in sector or k in product for k in ["médic", "medic", "pharma", "santé", "health", "clinical", "hospital"]):
        standards.append("ISO 13485:2016")
        standards.append("ISO 14971:2019")
    else:
        standards.append("ISO 9001:2015")
        
    # 2. Software/IT/Security/AI standards
    if any(k in product or k in sector for k in ["logiciel", "software", "connect", "app", "iot", "it", "numérique", "digital"]) or is_ai:
        standards.append("IEC 62304:2006/A1:2015")
        standards.append("ISO/IEC 27001:2022")
        if is_ai:
            standards.append("ISO/IEC 42001:2023 (Management de l'IA)")
        
    # 3. Market specific regulations
    if market == "CE":
        if any(k in sector or k in product for k in ["médic", "medic", "santé", "health"]):
            if "in vitro" in product or "ivd" in product:
                standards.append("Règlement (UE) 2017/746 (IVDR)")
            else:
                standards.append("Règlement (UE) 2017/745 (MDR)")
        if is_ai:
            standards.append("Règlement (UE) 2024/1689 (EU AI Act)")
        standards.append("Directive 2001/95/CE (Sécurité générale)")
    elif market == "FDA":
        if any(k in sector or k in product for k in ["médic", "medic", "santé", "health"]):
            standards.append("FDA 21 CFR Part 820 (QMSR 2026)")
            standards.append("FDA 21 CFR Part 11")
            if is_ai:
                standards.append("FDA PCCP Guidance (Aug 2025)")
        else:
            standards.append("FDA Food Safety Modernization Act")
    elif market == "UKCA":
        standards.append("UK Medical Devices Regulations 2002")
        standards.append("UK General Product Safety Regulations 2005")
    elif market == "FDI":
        standards.append("Norme FDI de Conformité")
    else:
        # Other or generic
        standards.append("ISO 14001:2015 (Environnement)")
        
    # 4. Privacy regulation if relevant
    if any(k in product or k in sector for k in ["connect", "app", "data", "donnée", "it", "logiciel", "software"]):
        if market == "CE":
            standards.append("RGPD (Règlement UE 2016/679)")
        else:
            standards.append("HIPAA (si données santé)" if "health" in sector or "santé" in sector else "ISO/IEC 27701")
            
    # Remove duplicates while maintaining order
    seen = set()
    unique_standards = []
    for s in standards:
        if s not in seen:
            seen.add(s)
            unique_standards.append(s)
            
    return unique_standards

def extract_json(text: str) -> list:
    """Extracts a JSON list from a text that might contain markdown or extra text."""
    try:
        # Try direct parsing
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find something that looks like a JSON list [ ... ]
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        
        # If it is a truncated or malformed JSON list, extract all quoted strings inside [ ...
        bracket_start = text.find('[')
        if bracket_start != -1:
            content_after_bracket = text[bracket_start:]
            # Find all double quoted strings that do not contain newlines
            items = re.findall(r'"([^"\n]+)"', content_after_bracket)
            if items:
                # Filter out empty or extremely long/weird strings
                valid_items = [item.strip() for item in items if item.strip() and len(item.strip()) < 100]
                if valid_items:
                    return valid_items

        # If it's a list of lines starting with - or *
        lines = re.findall(r'(?:^|\n)[-*]\s*(.*)', text)
        if lines:
            return [l.strip() for l in lines]
            
        return []

async def analyze_standards_ai(project_data: dict) -> list[str]:
    """
    MODE 1: Auto analysis
    Returns a list of applicable standards based on project data.
    """
    if not client:
        logger.info("Simulation mode: Returning smart fallback standards.")
        return get_smart_fallback_standards(project_data)

    prompt = f"""
    En tant qu'Expert Senior en Conformité Réglementaire, analyse les données suivantes et identifie la liste des 5 à 15 normes QMS et réglementations les plus pertinentes, applicables et RÉCENTES.
    
    Données du projet :
    - Entreprise : {project_data.get('company_name')}
    - Rôle : {project_data.get('company_role')}
    - Secteur : {project_data.get('activity_sector')}
    - Produit : {project_data.get('product')}
    - Marché : {project_data.get('market')}

    RÈGLES STRICTES :
    1. Limite-toi à une liste concise des 5 à 15 normes et réglementations les plus importantes et directement applicables.
    2. Propose SYSTÉMATIQUEMENT les versions et règlements les plus récents et en vigueur, notamment :
       - Le Règlement (UE) 2024/1689 (EU AI Act) et l'ISO/IEC 42001:2023 pour les projets impliquant de l'IA / Machine Learning.
       - La transition FDA QMSR (Quality Management System Regulation, 21 CFR Part 820 amendé en 2024, effectif depuis le 2 février 2026) incorporant l'ISO 13485:2016, plutôt que l'ancienne QSR de la FDA.
       - Le guide de la FDA sur les PCCP (Predetermined Change Control Plans, août 2025) pour les logiciels d'IA/ML en santé.
       - L'ISO/IEC 27001:2022 pour la cybersécurité.
       - L'ISO 13485:2016 pour les dispositifs médicaux.
       - L'ISO 9001:2015 pour le QMS général.
    3. Sois extrêmement précis (ex: cite l'année de la version de la norme si possible).
    4. Ne te limite pas au QMS de base, pense aux normes techniques spécifiques au produit ({project_data.get('product')}).
    5. Réponds UNIQUEMENT sous forme d'une liste JSON de chaînes de caractères.
    Format attendu : ["ISO 13485:2016", "Règlement (UE) 2024/1689 (EU AI Act)", "FDA 21 CFR Part 820 (QMSR 2026)", ...]
    6. Pas d'explications.
    """

    try:
        logger.info(f"Analyzing standards for project: {project_data}")
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "Tu es un expert QMS et conformité. Ta mission est de lister les normes les plus applicables et les plus récentes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
        )
        content = response.choices[0].message.content
        logger.info(f"AI Raw Response: {content}")
        standards = extract_json(content)
        
        if not standards:
            logger.warning(f"Failed to extract standards from AI response: {content}")
            return get_smart_fallback_standards(project_data)
            
        logger.info(f"Extracted standards: {standards}")
        return standards
    except Exception as e:
        logger.error(f"Error in analyze_standards_ai: {str(e)}", exc_info=True)
        return get_smart_fallback_standards(project_data)

async def chat_with_ai(project_data: dict, history: list[dict], message: str) -> str:
    """
    MODE 2: Interactive Chat
    Explains standards based on context.
    """
    if not client:
        return f"Simulation: Je ne peux pas répondre car l'API n'est pas configurée. Votre question était : '{message}'"

    system_prompt = f"""
    Tu es un Consultant Senior Expert de classe mondiale en Management de la Qualité (QMS) et en Affaires Réglementaires.
    Ton expertise couvre les normes, les réglementations européennes (MDR, IVDR, RGPD, EU AI Act 2024) et les exigences internationales (FDA 21 CFR Part 820, QMSR 2026, PCCP).
    CONTEXTE CLIENT :
    - Entreprise : {project_data.get('company_name')}
    - Rôle : {project_data.get('company_role')}
    - Secteur : {project_data.get('activity_sector')}
    - Produit : {project_data.get('product')}
    - Marché : {project_data.get('market')}
    - Normes déjà identifiées : {project_data.get('standards', 'Non spécifié')}

    MISSION :
    Accompagner le client de manière extrêmement précise, juste et sûre. Tes réponses doivent être irréprochables sur le plan réglementaire.

    DIRECTIVES STRICTES :
    1. PRIORITÉ AUX NORMES IDENTIFIÉES : Tes explications et conseils DOIVENT se concentrer en priorité sur les normes listées dans "Normes déjà identifiées" : {project_data.get('standards', 'Non spécifié')}. Ne propose d'autres normes que si elles sont absolument indispensables et absentes de la liste.
    2. NORMES ET RÈGLEMENTS LES PLUS RÉCENTS : Tu dois TOUJOURS orienter l'utilisateur vers les versions les plus récentes et en vigueur. Par exemple :
       - Le Règlement (UE) 2024/1689 (EU AI Act) pour les systèmes d'intelligence artificielle.
       - La transition FDA vers la QMSR (Quality Management System Regulation, 21 CFR Part 820 amendé en 2024, effectif depuis le 2 février 2026) incorporant l'ISO 13485:2016.
       - Le guide de la FDA sur les PCCP (Predetermined Change Control Plans, août 2025) pour les logiciels d'IA/ML en santé.
       - L'ISO/IEC 42001:2023 (Système de management de l'IA).
       - L'ISO/IEC 27001:2022 pour la sécurité de l'information.
       Ne suggère jamais de versions obsolètes ou dépassées.
    3. PRÉCISION ABSOLUE : Cite systématiquement les numéros de clauses ou articles précis.
    4. DISCRÉTION DU RÔLE : Ne répète jamais ton titre. Entre directement dans le sujet.
    5. MISE À JOUR DES NORMES : Si nécessaire, utilise le tag [UPDATE_STANDARDS]: ["Norme 1", ...] pour suggérer un changement.
    6. PERSONNALISATION : Adapte chaque réponse au produit ({project_data.get('product')}).
    7. LANGUE : Français ou anglais.

    Ton objectif est d'être le bras droit stratégique du Responsable Management de la Qualité.
    """

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.2, # Lower temperature for higher precision and reliability
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error in chat_with_ai: {str(e)}")
        return f"Désolé, une erreur technique est survenue lors de la communication avec l'IA. Détails : {str(e)}"
