"""Клиент для взаимодействия с LLM (DeepSeek / Ollama) и структурированного парсинга."""

import logging
import re

from openai import (
    APIConnectionError,
    AsyncOpenAI,
    BadRequestError,
    LengthFinishReasonError,
    RateLimitError,
)
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from prompt import FALLBACK_JSON_INSTRUCTION, SYSTEM_PROMPT, build_analysis_user_prompt
from schema import SentimentAnalysisResult

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
        self.extra_body = {"options": {"num_ctx": settings.llm_num_ctx}}

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
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
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=SentimentAnalysisResult,
                temperature=self.temperature,
                extra_body=self.extra_body,
            )

            parsed_result = response.choices[0].message.parsed
            if parsed_result is not None:
                raw_message = response.choices[0].message
                think_reasoning = getattr(raw_message, "reasoning", None)
                if think_reasoning and not parsed_result.reasoning:
                    parsed_result.reasoning = think_reasoning.strip()
                return parsed_result

        except (LengthFinishReasonError, ValidationError) as parse_err:
            logger.warning(
                "Метод .parse() вернул ошибку (%s). Применяем fallback с очисткой <think> тегов...",
                parse_err,
            )

        # 2. Fallback для моделей, выводящих нестандартный JSON или <think> теги
        raw_response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + FALLBACK_JSON_INSTRUCTION},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            extra_body=self.extra_body,
        )

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
