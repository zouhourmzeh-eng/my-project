import asyncio
import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.services.ai import analyze_standards_ai, init_client, client, model_name

async def main():
    print("OPENAI_API_KEY starts with:", settings.OPENAI_API_KEY[:8] if settings.OPENAI_API_KEY else "None")
    print("Initializing client...")
    init_client()
    print("Client initialized:", client is not None)
    print("Model name:", model_name)
    
    project_data = {
        "company_name": "TestCompany",
        "company_role": "Fabricant",
        "activity_sector": "Dispositifs Médicaux",
        "product": "Seringue connectée",
        "market": "CE"
    }
    
    print("\nRunning analyze_standards_ai...")
    try:
        standards = await analyze_standards_ai(project_data)
        print("Result:", standards)
    except Exception as e:
        print("Error encountered:", str(e))

if __name__ == "__main__":
    asyncio.run(main())
