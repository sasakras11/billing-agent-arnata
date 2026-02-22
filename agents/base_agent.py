"""Base class for AI agents."""
import logging

from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseAgent:
    """Base class providing shared LLM invocation for AI agents."""

    def __init__(self, db: Session, temperature: float = 0.3):
        self.db = db
        self.llm = ChatAnthropic(
            model=settings.llm_model,
            anthropic_api_key=settings.anthropic_api_key,
            temperature=temperature,
        )

    async def _invoke_llm(
        self,
        system_message: str,
        human_message: str,
        log_message: str = "",
    ) -> str:
        """Invoke LLM and return response content."""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_message),
            HumanMessage(content=human_message),
        ])
        response = await self.llm.ainvoke(prompt.format_messages())
        if log_message:
            logger.info(log_message)
        return response.content
