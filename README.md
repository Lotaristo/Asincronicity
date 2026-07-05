# День 1: базовый асинхронный HTTP-клиент

Минимальная реализация первого дня задания: класс `AsyncCrawler` загружает страницы через `aiohttp.ClientSession`, ограничивает конкурентность, использует connection pooling, обрабатывает сетевые ошибки, HTTP-ошибки и таймауты.

## Возможности

- `AsyncCrawler(max_concurrent=10)` с ограничением конкурентности;
- `fetch_url(url)` для загрузки одной страницы;
- `fetch_urls(urls)` для параллельной загрузки списка URL;
- общий `aiohttp.ClientSession` с `connect` и `sock_read` timeout;
- корректное закрытие через `close()`;
- базовое логирование начала, успеха и ошибок.

## Установка

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Пример использования

```python
import asyncio
from async_crawler import AsyncCrawler

async def main():
    crawler = AsyncCrawler(max_concurrent=5)
    urls = [
        "https://example.com",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/2",
    ]
    results = await crawler.fetch_urls(urls)
    await crawler.close()
    print(f"Загружено {sum(bool(page) for page in results.values())} страниц")

asyncio.run(main())
```

## Демонстрация

```powershell
python examples/day1_demo.py
```

## Проверки

```powershell
ruff check .
pytest
```