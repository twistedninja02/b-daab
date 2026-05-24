"""
B-DAAB SQL Generation Agent
Uses LLMs to convert Bengali queries to SQL
"""

import logging
import re
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    MOCK = "mock"


@dataclass
class AgentConfig:
    provider: LLMProvider = LLMProvider.MOCK
    model: str = "claude-3.5-sonnet"
    temperature: float = 0.0
    max_tokens: int = 500
    use_few_shot: bool = True
    few_shot_count: int = 3
    max_retries: int = 3
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@dataclass
class AgentResponse:
    success: bool
    sql: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: float = 0.0
    error: Optional[str] = None
    error_type: Optional[str] = None
    attempts: int = 0
    model_used: str = ""
    tokens_used: int = 0


class LLMClient(ABC):
    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 500
    ) -> tuple[str, int]:
        pass


class MockLLMClient(LLMClient):
    PATTERNS = {
        'সকল': 'SELECT * FROM',
        'কতটি': 'SELECT COUNT(*) FROM',
        'ঢাকা': "WHERE city = 'Dhaka'",
        'হাসপাতাল': 'hospitals',
        'স্কুল': 'schools',
    }

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 500
    ) -> tuple[str, int]:
        logger.debug("Using MockLLMClient")
        result = "SELECT * FROM hospitals;"
        for pattern, replacement in self.PATTERNS.items():
            if pattern in user_prompt:
                result = replacement
                break
        return result, 50


class AnthropicClient(LLMClient):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            logger.debug("Initialized Anthropic client")
        except ImportError:
            logger.warning("anthropic package not installed")
            self.client = None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 500
    ) -> tuple[str, int]:
        if self.client is None:
            return "", 0
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            text = message.content[0].text
            tokens = message.usage.output_tokens
            logger.debug(f"Generated {tokens} tokens from Anthropic")
            return text, tokens
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class OpenAIClient(LLMClient):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            logger.debug("Initialized OpenAI client")
        except ImportError:
            logger.warning("openai package not installed")
            self.client = None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 500
    ) -> tuple[str, int]:
        if self.client is None:
            return "", 0
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            text = response.choices[0].message.content
            tokens = response.usage.completion_tokens
            logger.debug(f"Generated {tokens} tokens from OpenAI")
            return text, tokens
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class OllamaClient(LLMClient):
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        try:
            import requests
            self.requests = requests
            logger.debug(f"Initialized Ollama client ({base_url})")
        except ImportError:
            logger.warning("requests package not installed")
            self.requests = None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 500
    ) -> tuple[str, int]:
        if self.requests is None:
            return "", 0
        try:
            response = self.requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": "mistral",
                    "prompt": f"{system_prompt}\n{user_prompt}",
                    "temperature": temperature,
                    "stream": False
                }
            )
            text = response.json().get('response', '')
            tokens = len(text.split())
            logger.debug("Generated from Ollama")
            return text, tokens
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise


class SQLExtractor:
    @staticmethod
    def extract(response: str) -> Optional[str]:
        match = re.search(r'```sql\n(.*?)\n```', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        match = re.search(r'```\n(.*?)\n```', response, re.DOTALL)
        if match:
            sql = match.group(1).strip()
            if sql.upper().startswith('SELECT'):
                return sql

        match = re.search(r'(SELECT\s+.*?[;]?)', response, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1).strip()
            if not sql.endswith(';'):
                sql += ';'
            return sql

        for line in response.split('\n'):
            line = line.strip()
            if line.upper().startswith('SELECT'):
                return line

        return None


class SQLPlanner:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm_client = self._init_llm_client()
        self.logger = logger

    def _init_llm_client(self) -> LLMClient:
        if self.config.provider == LLMProvider.ANTHROPIC:
            return AnthropicClient(api_key=self.config.api_key)
        elif self.config.provider == LLMProvider.OPENAI:
            return OpenAIClient(api_key=self.config.api_key)
        elif self.config.provider == LLMProvider.OLLAMA:
            return OllamaClient(base_url=self.config.base_url or "http://localhost:11434")
        else:
            return MockLLMClient()

    def plan(
        self,
        bengali_query: str,
        english_gloss: str = "",
        schema_info: str = ""
    ) -> AgentResponse:
        self.logger.info(f"Planning SQL for: {bengali_query[:50]}...")

        response = AgentResponse(success=False, model_used=self.config.model)

        if not schema_info:
            schema_info = self._get_default_schema()

        for attempt in range(1, self.config.max_retries + 1):
            response.attempts = attempt

            try:
                from agent.prompt import PromptBuilder, PromptTemplate

                builder = PromptBuilder(PromptTemplate.BASIC)
                system_prompt, user_prompt = builder.build_full_prompt(
                    bengali_query=bengali_query,
                    english_gloss=english_gloss,
                    schema_info=schema_info
                )

                self.logger.debug(f"Attempt {attempt}/{self.config.max_retries}")

                llm_response, tokens = self.llm_client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )

                response.tokens_used = tokens
                response.reasoning = llm_response

                extracted_sql = SQLExtractor.extract(llm_response)

                if extracted_sql:
                    response.sql = extracted_sql
                    response.success = True
                    response.confidence = 0.95
                    self.logger.info(f"✓ Generated SQL (attempt {attempt})")
                    return response

            except Exception as e:
                self.logger.warning(f"Attempt {attempt} failed: {e}")
                response.error = str(e)
                response.error_type = type(e).__name__

        response.error = "Failed to generate valid SQL after all attempts"
        response.success = False
        response.confidence = 0.0

        return response

    def plan_batch(self, queries_dict: Dict[str, str]) -> Dict[str, AgentResponse]:
        self.logger.info(f"Planning {len(queries_dict)} queries")
        results = {}
        for query_id, query_text in queries_dict.items():
            result = self.plan(query_text)
            results[query_id] = result
        successful = sum(1 for r in results.values() if r.success)
        self.logger.info(f"✓ Completed batch: {successful}/{len(queries_dict)} successful")
        return results

    def _get_default_schema(self) -> str:
        return """
Tables:
- hospitals (id, name, city)
- patients (id, name, hospital_id)
- schools (id, name, city)
- students (id, name, school_id)
- shops (id, name, owner_name, city)
- products (id, name, shop_id, price)
"""
