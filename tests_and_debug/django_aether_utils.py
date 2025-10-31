# utils/aether_connection.py
from django.conf import settings
from aethermagic import AetherMagic, ProtocolType
import logging

logger = logging.getLogger(__name__)

_aether_instance = None

def get_aether_magic():
    """
    Singleton для AetherMagic подключения
    Использует настройки из Django settings
    """
    global _aether_instance
    
    if _aether_instance is None:
        _aether_instance = create_aether_magic()
    
    return _aether_instance

def create_aether_magic():
    """
    Создает AetherMagic подключение из настроек Django
    """
    try:
        # Вариант 1: Используем AETHER_CONFIG (рекомендуется)
        if hasattr(settings, 'AETHER_CONFIG'):
            config = settings.AETHER_CONFIG
            
            # Определяем тип протокола
            protocol_map = {
                'mqtt': ProtocolType.MQTT,
                'redis': ProtocolType.REDIS,
                'websocket': ProtocolType.WEBSOCKET,
                'zeromq': ProtocolType.ZEROMQ
            }
            
            protocol_type = protocol_map.get(
                config.get('protocol_type', 'mqtt'), 
                ProtocolType.MQTT
            )
            
            aether = AetherMagic(
                protocol_type=protocol_type,
                host=config.get('host', 'localhost'),
                port=config.get('port', 1883),
                ssl=config.get('ssl', False),
                username=config.get('username', ''),
                password=config.get('password', ''),
                union=config.get('union', 'default')
            )
            
        # Вариант 2: Используем отдельные настройки (обратная совместимость)
        elif hasattr(settings, 'MQTT_BROKER'):
            aether = AetherMagic(
                server=settings.MQTT_BROKER,
                port=getattr(settings, 'MQTT_PORT', 1883),
                ssl=getattr(settings, 'MQTT_SSL', False),
                user=getattr(settings, 'MQTT_USER', ''),
                password=getattr(settings, 'MQTT_PASSWORD', ''),
                union=getattr(settings, 'AETHER_UNION', 'default')
            )
            
        else:
            # Настройки по умолчанию для разработки
            logger.warning("AetherMagic settings not found, using defaults")
            aether = AetherMagic(
                server='localhost',
                port=1883,
                union='development'
            )
            
        logger.info(f"AetherMagic created: {type(aether.protocol).__name__}")
        return aether
        
    except Exception as e:
        logger.error(f"Failed to create AetherMagic: {e}")
        raise

async def connect_aether():
    """
    Подключает AetherMagic (вызывать при старте приложения)
    """
    aether = get_aether_magic()
    try:
        await aether.connect()
        logger.info("AetherMagic connected successfully")
        return aether
    except Exception as e:
        logger.error(f"Failed to connect AetherMagic: {e}")
        raise

async def disconnect_aether():
    """
    Отключает AetherMagic (вызывать при завершении приложения)
    """
    global _aether_instance
    if _aether_instance:
        try:
            await _aether_instance.disconnect()
            logger.info("AetherMagic disconnected")
        except Exception as e:
            logger.error(f"Failed to disconnect AetherMagic: {e}")
        finally:
            _aether_instance = None

# Convenience функции для быстрого использования
async def aether_perform_task(job, task, context, data, shared=False):
    """Удобная функция для отправки задач"""
    aether = get_aether_magic()
    return await aether.perform_task(job, task, context, data, shared=shared)

async def aether_add_task(job, task, context, callback, shared=False):
    """Удобная функция для подписки на задачи"""
    aether = get_aether_magic()
    return await aether.add_task(job, task, context, callback, shared=shared)