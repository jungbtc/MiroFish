"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config
from ..llm_settings import (
    reasoning_request_kwargs,
    structured_output_reasoning_effort,
    temperature_request_kwargs,
    token_limit_request_kwargs,
    usage_to_log_dict,
    uses_completion_token_param,
    validate_model,
    validate_reasoning_effort,
)
from ..utils.logger import get_logger


logger = get_logger('mirofish.llm')


class LLMClient:
    """LLM客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = validate_model(model or Config.LLM_MODEL_NAME)
        self.reasoning_effort = validate_reasoning_effort(
            reasoning_effort or Config.LLM_REASONING_EFFORT
        )

        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        reasoning_effort: Optional[str] = None,
    ) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）
            
        Returns:
            模型响应文本
        """
        effective_reasoning_effort = validate_reasoning_effort(
            reasoning_effort or self.reasoning_effort
        )
        kwargs = self._build_chat_kwargs(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            reasoning_effort=effective_reasoning_effort,
        )

        logger.info(
            "LLM request start: model=%s, reasoning_effort=%s, effective_reasoning_effort=%s",
            self.model,
            self.reasoning_effort,
            effective_reasoning_effort,
        )
        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            logger.error(
                "LLM request error: model=%s, reasoning_effort=%s, effective_reasoning_effort=%s, error=%s",
                self.model,
                self.reasoning_effort,
                effective_reasoning_effort,
                exc,
            )
            raise

        usage = usage_to_log_dict(response)
        logger.info(
            "LLM request complete: model=%s, reasoning_effort=%s, effective_reasoning_effort=%s, usage=%s",
            self.model,
            self.reasoning_effort,
            effective_reasoning_effort,
            usage,
        )
        content = response.choices[0].message.content or ""
        # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        if not content:
            logger.error(
                "LLM request returned empty content: model=%s, reasoning_effort=%s, effective_reasoning_effort=%s, usage=%s",
                self.model,
                self.reasoning_effort,
                effective_reasoning_effort,
                usage,
            )
        return content

    def _build_chat_kwargs(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict] = None,
        reasoning_effort: Optional[str] = None,
    ) -> Dict[str, Any]:
        effective_reasoning_effort = validate_reasoning_effort(
            reasoning_effort or self.reasoning_effort
        )
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            **reasoning_request_kwargs(
                effective_reasoning_effort,
                self.model,
                self.base_url,
            ),
            **temperature_request_kwargs(self.model, temperature, self.base_url),
            **token_limit_request_kwargs(
                self.model,
                effective_reasoning_effort,
                max_tokens,
                self._uses_completion_token_param(),
            ),
        }

        if response_format:
            kwargs["response_format"] = response_format

        return kwargs

    def _uses_completion_token_param(self) -> bool:
        """Newer OpenAI chat models reject max_tokens and require max_completion_tokens."""
        return uses_completion_token_param(self.model, self.base_url)
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            解析后的JSON对象
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            reasoning_effort=structured_output_reasoning_effort(self.reasoning_effort),
        )
        # 清理markdown代码块标记
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()
        if not cleaned_response:
            raise ValueError(
                "LLM返回空JSON内容，可能是推理token耗尽了输出预算；"
                "请降低 reasoning_effort 或增大 max_tokens"
            )

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned_response}")
