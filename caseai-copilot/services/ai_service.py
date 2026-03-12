"""
AI service layer for CaseAI Copilot.
Wraps the Anthropic Claude API with error handling and audit logging.
"""
import anthropic

from utils.logger import get_logger, log_ai_call
from utils.formatting import parse_ai_json


class AIService:
    """
    Service for interacting with the Anthropic Claude API.
    Handles API calls, error handling, and audit logging.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-6",
        max_tokens: int = 4096,
    ):
        """
        Initialize the AI service.

        Args:
            api_key:    Anthropic API key.
            model:      Model ID to use (default: claude-opus-4-6).
            max_tokens: Maximum tokens for response (default: 4096).
        """
        self.model = model
        self.max_tokens = max_tokens
        self._logger = get_logger("caseai.ai_service")

        if not api_key:
            self._logger.warning(
                "AIService initialized without an API key. "
                "All AI calls will fail until a valid key is provided."
            )
            self._client = None
        else:
            self._client = anthropic.Anthropic(api_key=api_key)
            self._logger.info(
                f"AIService initialized | model={self.model} | max_tokens={self.max_tokens}"
            )

    def call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        feature_name: str = "unknown",
    ) -> str:
        """
        Call the Claude API and return the response text.

        Args:
            system_prompt: The system-level instruction prompt.
            user_prompt:   The user message / case context prompt.
            feature_name:  Name of the feature calling this (for audit logging).

        Returns:
            Response text string, or empty string on failure.
        """
        if self._client is None:
            self._logger.error(
                "call_claude: No Anthropic client available. API key is missing."
            )
            raise ValueError(
                "Anthropic API key is not configured. "
                "Please set ANTHROPIC_API_KEY in your .env file."
            )

        try:
            self._logger.debug(
                f"Calling Claude | feature={feature_name} | "
                f"system_len={len(system_prompt)} | user_len={len(user_prompt)}"
            )

            message = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            response_text = message.content[0].text

            # Audit log
            input_tokens = getattr(message.usage, "input_tokens", None)
            output_tokens = getattr(message.usage, "output_tokens", None)
            total_tokens = (
                (input_tokens or 0) + (output_tokens or 0)
                if input_tokens is not None
                else None
            )
            log_ai_call(
                model=self.model,
                feature=feature_name,
                token_count=total_tokens,
                logger=self._logger,
            )

            return response_text

        except anthropic.AuthenticationError as exc:
            self._logger.error(
                f"call_claude: Authentication failed for feature={feature_name}. "
                f"Check that your ANTHROPIC_API_KEY is valid. Error: {exc}"
            )
            raise ValueError(
                "Authentication failed. Your Anthropic API key appears to be invalid. "
                "Please verify ANTHROPIC_API_KEY in your .env file."
            ) from exc

        except anthropic.APIStatusError as exc:
            self._logger.error(
                f"call_claude: API status error for feature={feature_name}. "
                f"Status: {exc.status_code}. Error: {exc.message}"
            )
            raise RuntimeError(
                f"Anthropic API returned an error (HTTP {exc.status_code}): {exc.message}"
            ) from exc

        except anthropic.APIConnectionError as exc:
            self._logger.error(
                f"call_claude: Connection error for feature={feature_name}. Error: {exc}"
            )
            raise RuntimeError(
                "Could not connect to the Anthropic API. "
                "Please check your internet connection and try again."
            ) from exc

        except Exception as exc:
            self._logger.error(
                f"call_claude: Unexpected error for feature={feature_name}. Error: {exc}",
                exc_info=True,
            )
            raise RuntimeError(
                f"An unexpected error occurred while calling the AI service: {exc}"
            ) from exc

    def call_claude_for_json(
        self,
        system_prompt: str,
        user_prompt: str,
        feature_name: str = "unknown",
    ):
        """
        Call Claude and parse the response as JSON.

        Returns:
            Parsed list or dict. Returns empty list on parse failure.
        """
        try:
            response_text = self.call_claude(system_prompt, user_prompt, feature_name)
            return parse_ai_json(response_text)
        except Exception as exc:
            self._logger.error(
                f"call_claude_for_json: failed for feature={feature_name}. Error: {exc}"
            )
            return []
