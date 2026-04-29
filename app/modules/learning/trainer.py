import asyncio
from app.modules.learning.service import learning_service

async def train_all_domains(domains: list = None):
    if not domains:
        domains = ["general", "security", "compliance", "risk", "operations"]
    
    print(f"🚀 Starting Data Discovery and Training for {len(domains)} domains...")
    
    for domain in domains:
        print(f"\n[{domain.upper()}] Training...")
        try:
            success, message = await learning_service.discover_and_learn(domain)
            if success:
                print(f"✅ Training Complete for {domain}")
            else:
                print(f"❌ Training Failed for {domain}: {message}")
        except Exception as e:
            print(f"❌ Error during training of {domain}: {e}")

    print("\n✨ All domains updated! System is now smarter about the database patterns.")

if __name__ == "__main__":
    asyncio.run(train_all_domains())
