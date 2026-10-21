"""Клиент для взаимодействия с LLM (DeepSeek / Ollama) и структурированного парсинга."""

import logging
import re

from config import settings
from openai import (
    APIConnectionError,
    AsyncOpenAI,
    BadRequestError,
    InternalServerError,
    LengthFinishReasonError,
    RateLimitError,
)
from prompt import FALLBACK_JSON_INSTRUCTION, SYSTEM_PROMPT, build_analysis_user_prompt
from pydantic import ValidationError
from schema import SentimentAnalysisResult
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Регулярные выражения для очистки вывода модели
THINK_TAG_REGEX = re.compile(r"<think>.*?</think>", re.DOTALL)
JSON_CODEBLOCK_REGEX = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class SentimentAnalyzer:
    """Анализатор новостей через LLM с гарантированным Pydantic-выводом и поддержкой DeepSeek R1."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key or "ollama",
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout,
        )
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        # Параметры options (num_ctx) передаем только для локальной Ollama
        is_ollama = "11434" in str(settings.llm_base_url) or "ollama" in str(settings.llm_base_url).lower()
        self.extra_body = {"options": {"num_ctx": settings.llm_num_ctx}} if is_ollama else None

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, InternalServerError)),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        stop=stop_after_attempt(settings.llm_max_retries),
        reraise=True,
    )
    async def analyze_article(
        self,
        title: str,
        content: str,
        source: str,
        categories: list[str],
    ) -> SentimentAnalysisResult:
        """Анализирует статью и возвращает строго типизированный SentimentAnalysisResult."""
        try:
            return await self._run_analysis(
                title=title,
                content=content,
                source=source,
                categories=categories,
                max_chars=settings.max_content_chars,
            )
        except BadRequestError as bad_req_err:
            err_msg = str(bad_req_err).lower()
            if "context" in err_msg or "exceed" in err_msg or "token" in err_msg:
                logger.warning(
                    "Контекст модели превышен для статьи '%s'. "
                    "Повторный анализ с сокращением текста до 2000 символов...",
                    title[:50],
                )
                return await self._run_analysis(
                    title=title,
                    content=content,
                    source=source,
                    categories=categories,
                    max_chars=2000,
                )
            raise

    async def _run_analysis(
        self,
        title: str,
        content: str,
        source: str,
        categories: list[str],
        max_chars: int,
    ) -> SentimentAnalysisResult:
        """Внутренний метод инференса с попыткой Structured Output и fallback'ом."""
        user_prompt = build_analysis_user_prompt(
            title=title,
            source=source,
            categories=categories,
            content=content,
            max_chars=max_chars,
        )

        logger.debug("Отправка статьи '%s' на анализ в модель %s...", title[:50], self.model)

        # 1. Попытка через стандартный Structured Outputs метод .parse()
        try:
            parse_kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT + FALLBACK_JSON_INSTRUCTION},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": SentimentAnalysisResult,
                "temperature": self.temperature,
            }
            if self.extra_body:
                parse_kwargs["extra_body"] = self.extra_body

            response = await self.client.beta.chat.completions.parse(**parse_kwargs)

            parsed_result = response.choices[0].message.parsed
            if parsed_result is not None:
                raw_message = response.choices[0].message
                think_reasoning = getattr(raw_message, "reasoning", None)
                if think_reasoning and not parsed_result.reasoning:
                    parsed_result.reasoning = think_reasoning.strip()
                return parsed_result

        except (LengthFinishReasonError, ValidationError, BadRequestError) as parse_err:
            # Оптимизация для локальных моделей (Qwen / DeepSeek): если модель вернула валидный
            # JSON, но обернула его в markdown ```json, восстанавливаем результат напрямую без
            # долгого повторного запроса к LLM.
            raw_content = None
            if isinstance(parse_err, ValidationError):
                errors = parse_err.errors()
                if errors and "input" in errors[0]:
                    raw_content = str(errors[0]["input"])
            elif isinstance(parse_err, LengthFinishReasonError) and hasattr(parse_err, "completion"):
                raw_content = parse_err.completion.choices[0].message.content

            if raw_content:
                try:
                    clean_json = self._extract_json_from_text(raw_content)
                    return SentimentAnalysisResult.model_validate_json(clean_json)
                except (ValidationError, ValueError):
                    pass

            logger.warning(
                "Метод .parse() вернул ошибку (%s). Применяем fallback с очисткой и JSON-парсингом...",
                parse_err,
            )

        # 2. Fallback для моделей, выводящих нестандартный JSON или <think> теги
        fallback_kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT + FALLBACK_JSON_INSTRUCTION},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }
        if self.extra_body:
            fallback_kwargs["extra_body"] = self.extra_body

        raw_response = await self.client.chat.completions.create(**fallback_kwargs)

        content_text = raw_response.choices[0].message.content or ""
        clean_json = self._extract_json_from_text(content_text)

        return SentimentAnalysisResult.model_validate_json(clean_json)

    @staticmethod
    def _extract_json_from_text(text: str) -> str:
        """Очищает текст от тегов <think>...</think>, markdown-блоков и извлекает чистый JSON."""
        # Удаляем теги рассуждений DeepSeek <think>...</think>
        cleaned = THINK_TAG_REGEX.sub("", text).strip()

        # Ищем блок markdown ```json ... ```
        md_match = JSON_CODEBLOCK_REGEX.search(cleaned)
        if md_match:
            return md_match.group(1).strip()

        # Ищем первый { и последний }
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return cleaned[start_idx : end_idx + 1].strip()

        return cleaned
