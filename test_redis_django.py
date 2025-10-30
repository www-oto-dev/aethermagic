# test_redis_connection.py
import asyncio
from django.conf import settings
from utils.aether_connection import get_aether_magic

async def test_redis_aether():
    """Тест подключения AetherMagic к Redis"""
    try:
        # Получаем настроенный AetherMagic
        aether = get_aether_magic()
        print(f"Protocol: {type(aether.protocol).__name__}")
        print(f"Host: {aether.protocol.config.host}")
        print(f"Port: {aether.protocol.config.port}")
        
        # Подключаемся
        await aether.connect()
        print("✅ Connected to Redis successfully!")
        
        # Тестируем отправку задачи
        await aether.perform_task(
            job="test",
            task="hello",
            context="demo",
            data={"message": "Hello from AetherMagic + Redis!"},
            shared=False
        )
        print("✅ Task sent successfully!")
        
        # Отключаемся
        await aether.disconnect()
        print("✅ Disconnected successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_redis_aether())