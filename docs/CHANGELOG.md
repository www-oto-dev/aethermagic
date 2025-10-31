# CHANGELOG

## [0.1.0] - Multi-Protocol Support

### 🎉 Новые возможности

#### Поддержка множественных протоколов коммуникации:

1. **Redis Pub/Sub** 
   - Быстрая доставка сообщений в памяти
   - Поддержка wildcard паттернов
   - Базовый класс: `RedisProtocol`

2. **Redis Streams**
   - Надежная доставка с гарантиями
   - Consumer groups для балансировки нагрузки
   - Персистентность сообщений
   - Класс: `RedisStreamProtocol`

3. **HTTP/WebSocket**
   - REST API для надежной доставки
   - WebSocket для real-time коммуникации
   - Режимы сервера и клиента
   - Класс: `HTTPWebSocketProtocol`

4. **ZeroMQ**
   - Высокопроизводительный messaging
   - Паттерны: PUB/SUB, PUSH/PULL, REQ/REP
   - Работа без брокера
   - Класс: `ZeroMQProtocol`

#### Архитектурные улучшения:

- **Единый интерфейс**: `ProtocolInterface` для всех протоколов
- **Фабрика протоколов**: `ProtocolFactory` для создания инстансов
- **Унифицированные сообщения**: `AetherMessage` класс
- **Конфигурация**: `ConnectionConfig` для настройки
- **Enum протоколов**: `ProtocolType` для типизации

#### Обратная совместимость:

- Полная совместимость с существующим MQTT кодом
- `AetherMagic` теперь алиас для `MultiProtocolAetherMagic`
- Старые методы работают без изменений

### 📁 Структура файлов

```
src/aethermagic/
├── __init__.py                          # Обновлен для экспорта новых классов
├── magic.py                             # Оригинальная MQTT реализация
├── task.py                              # Без изменений
├── multi_magic.py                       # Новый мульти-протокольный класс
└── protocols/
    ├── __init__.py                      # Базовые интерфейсы и классы
    ├── redis_protocol.py                # Redis Pub/Sub и Streams
    ├── http_websocket_protocol.py       # HTTP/WebSocket реализация
    └── zeromq_protocol.py               # ZeroMQ реализация
```

### 🔧 Новые зависимости

```
# Redis support
redis>=4.0.0

# HTTP/WebSocket support  
aiohttp>=3.8.0
websockets>=10.0

# ZeroMQ support
pyzmq>=24.0.0
```

### 📝 Примеры использования

Добавлены файлы:
- `examples.py` - Полные примеры каждого протокола
- `demo.py` - Интерактивная демонстрация
- `test_protocols.py` - Автоматические тесты
- `quick_redis_test.py` - Быстрый тест Redis
- `MULTI_PROTOCOL_README.md` - Документация

### 🚀 Использование

```python
from aethermagic import AetherMagic, ProtocolType

# Redis
aether = AetherMagic(protocol_type=ProtocolType.REDIS)

# HTTP/WebSocket
aether = AetherMagic(protocol_type=ProtocolType.HTTP)

# ZeroMQ
aether = AetherMagic(protocol_type=ProtocolType.ZEROMQ)

# MQTT (как раньше)
aether = AetherMagic(protocol_type=ProtocolType.MQTT)
```

### 📊 Сравнение протоколов

| Протокол | Производительность | Надежность | Сложность | Случаи использования |
|----------|-------------------|------------|-----------|---------------------|
| MQTT | Средняя | Высокая | Низкая | IoT, легковесные системы |
| Redis Pub/Sub | Высокая | Средняя | Низкая | Быстрые уведомления |
| Redis Streams | Высокая | Высокая | Средняя | Надежная обработка задач |
| HTTP/WebSocket | Средняя | Высокая | Средняя | Веб-интеграция |
| ZeroMQ | Очень высокая | Средняя | Высокая | Высоконагруженные системы |

---

## [0.0.11] - Исходная MQTT реализация

Базовая функциональность с поддержкой только MQTT протокола.