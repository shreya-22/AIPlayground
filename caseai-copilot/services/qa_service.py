"""
Q&A service for CaseAI Copilot.
Provides grounded question-answering strictly from case context.
"""
from typing import List

from models.schemas import CaseContext
from models.dto import metadata_to_text, notes_to_text, visits_to_text, activity_to_text, medication_to_text
from config.prompts import SYSTEM_PROMPT_BASE, build_qa_prompt
from services.ai_service import AIService
from utils.guards import validate_user_question
from utils.logger import get_logger

_logger = get_logger("caseai.qa_service")

_FALLBACK_MESSAGE = (
    "I was unable to answer that question. Please try again. "
    "If the issue persists, check that the AI service is properly configured."
)

_SUGGESTED_QUESTIONS = [
    "What is the patient's current status and most recent contact date?",
    "What medications is the patient currently on and are there any adherence concerns?",
    "What follow-up actions are pending or overdue for this case?",
    "Has this patient missed any appointments or failed outreach attempts?",
    "Is there a caregiver documented and have any caregiver concerns been noted?",
    "What was the reason this case was opened?",
    "Are there any documentation gaps or unresolved referrals in this case?",
    "What progress has been made since the case was opened?",
]


class QAService:
    """
    Service for answering natural language questions about a specific case.
    All answers are grounded strictly in the provided case context.
    """

    def __init__(self, ai_service: AIService):
        """
        Initialize QAService.

        Args:
            ai_service: An initialized AIService instance.
        """
        self.ai_service = ai_service

    def answer_question(self, context: CaseContext, question: str) -> str:
        """
        Answer a question about a specific case using the case context.

        Args:
            context:  The full CaseContext to query.
            question: The user's natural language question.

        Returns:
            Answer string grounded in case data, or a fallback error message.
        """
        # Validate the question
        is_valid, error_message = validate_user_question(question)
        if not is_valid:
            _logger.warning(
                f"QAService.answer_question: question validation failed: {error_message}"
            )
            return f"Question could not be processed: {error_message}"

        try:
            metadata_text = metadata_to_text(context.case_metadata)
            notes_text = notes_to_text(context.notes)
            structured_text = (
                "=== VISITS ===\n" + visits_to_text(context.visits) + "\n\n"
                "=== ACTIVITIES ===\n" + activity_to_text(context.activities) + "\n\n"
                "=== MEDICATIONS ===\n" + medication_to_text(context.medication_events)
            )

            user_prompt = build_qa_prompt(
                case_metadata=metadata_text,
                notes_text=notes_text,
                structured_data=structured_text,
                user_question=question,
            )

            answer = self.ai_service.call_claude(
                system_prompt=SYSTEM_PROMPT_BASE,
                user_prompt=user_prompt,
                feature_name="qa",
            )

            if not answer or not answer.strip():
                _logger.warning(
                    f"QAService.answer_question: received empty response for "
                    f"case {context.case_metadata.case_id}."
                )
                return _FALLBACK_MESSAGE

            _logger.info(
                f"QAService.answer_question: answered question for "
                f"case {context.case_metadata.case_id}."
            )
            return answer.strip()

        except Exception as exc:
            _logger.error(
                f"QAService.answer_question: failed for case "
                f"{context.case_metadata.case_id}: {exc}"
            )
            return _FALLBACK_MESSAGE

    @staticmethod
    def get_suggested_questions() -> List[str]:
        """
        Return a curated list of suggested questions for the UI.

        Returns:
            List of question strings.
        """
        return _SUGGESTED_QUESTIONS.copy()
