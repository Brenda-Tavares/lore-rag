import httpx
from app.core.config import settings
import asyncio
import hashlib
import json
from pathlib import Path

class LLMClient:
    def __init__(self):
        # OpenRouter (para embeddings)
        self.openrouter_url = "https://openrouter.ai/api/v1"
        self.openrouter_headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://lore-rag.local",
            "X-Title": settings.APP_NAME
        }
        
        # Groq (para chat)
        self.groq_url = "https://api.groq.com/openai/v1"
        self.groq_headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        self.max_retries = 3
        self.base_delay = 5
        
        # Cache de embeddings
        self.cache_dir = Path("./embedding_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "embeddings.json"
        self.embedding_cache = self._load_cache()
        print(f"[CACHE] Embeddings cache loaded: {len(self.embedding_cache)} entries")

    def _load_cache(self) -> dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[CACHE] Failed to load cache: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.embedding_cache, f)
        except Exception as e:
            print(f"[CACHE] Failed to save cache: {e}")

    def _get_cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generates vector embedding using OpenRouter (with caching).
        """
        cache_key = self._get_cache_key(text)
        
        if cache_key in self.embedding_cache:
            print(f"[CACHE] Embedding hit")
            return self.embedding_cache[cache_key]
        
        print(f"[EMBEDDING] Cache miss, calling OpenRouter API...")
        
        async with httpx.AsyncClient() as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(
                        f"{self.openrouter_url}/embeddings",
                        headers=self.openrouter_headers,
                        json={
                            "model": settings.EMBEDDING_MODEL,
                            "input": text
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 401:
                        raise ValueError("OpenRouter API key is invalid.")
                    
                    if response.status_code == 429:
                        delay = self.base_delay * (2 ** attempt)
                        print(f"[WARNING] 429 Rate Limit (attempt {attempt + 1}/{self.max_retries}). Waiting {delay}s...")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise ValueError("OpenRouter rate limit exceeded.")
                    
                    response.raise_for_status()
                    embedding = response.json()["data"][0]["embedding"]
                    
                    self.embedding_cache[cache_key] = embedding
                    self._save_cache()
                    
                    return embedding
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < self.max_retries - 1:
                        delay = self.base_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    raise

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in a single API call.
        """
        results = []
        texts_to_process = []
        indices_to_process = []
        
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self.embedding_cache:
                results.append((i, self.embedding_cache[cache_key]))
            else:
                texts_to_process.append(text)
                indices_to_process.append(i)
        
        if not texts_to_process:
            print(f"[CACHE] All {len(texts)} embeddings were cached!")
            return [r[1] for r in sorted(results, key=lambda x: x[0])]
        
        print(f"[EMBEDDING] Batch: {len(texts) - len(texts_to_process)} cached, {len(texts_to_process)} to process")
        
        async with httpx.AsyncClient() as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(
                        f"{self.openrouter_url}/embeddings",
                        headers=self.openrouter_headers,
                        json={
                            "model": settings.EMBEDDING_MODEL,
                            "input": texts_to_process
                        },
                        timeout=60.0
                    )
                    
                    if response.status_code == 429:
                        delay = self.base_delay * (2 ** attempt)
                        print(f"[WARNING] 429 Rate Limit (attempt {attempt + 1}/{self.max_retries}). Waiting {delay}s...")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise ValueError("OpenRouter rate limit exceeded.")
                    
                    response.raise_for_status()
                    data = response.json()["data"]
                    
                    for idx, item in enumerate(data):
                        text = texts_to_process[idx]
                        cache_key = self._get_cache_key(text)
                        self.embedding_cache[cache_key] = item["embedding"]
                        results.append((indices_to_process[idx], item["embedding"]))
                    
                    self._save_cache()
                    
                    return [r[1] for r in sorted(results, key=lambda x: x[0])]
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < self.max_retries - 1:
                        delay = self.base_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    raise

    async def chat_completion(self, messages: list[dict]) -> str:
        """
        Generates chat completion using GROQ (much higher rate limits).
        """
        print(f"[CHAT] Using Groq with model: {settings.DEFAULT_LLM_MODEL}")
        
        async with httpx.AsyncClient() as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(
                        f"{self.groq_url}/chat/completions",
                        headers=self.groq_headers,
                        json={
                            "model": settings.DEFAULT_LLM_MODEL,
                            "messages": messages,
                            "temperature": 0.3,
                            "max_tokens": 1000
                        },
                        timeout=60.0
                    )
                    
                    if response.status_code == 401:
                        raise ValueError("Groq API key is invalid.")
                    
                    if response.status_code == 429:
                        delay = self.base_delay * (2 ** attempt)
                        print(f"[WARNING] 429 Rate Limit no Groq (attempt {attempt + 1}/{self.max_retries}). Waiting {delay}s...")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise ValueError("Groq rate limit exceeded.")
                    
                    response.raise_for_status()
                    return response.json()["choices"][0]["message"]["content"]
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < self.max_retries - 1:
                        delay = self.base_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    raise