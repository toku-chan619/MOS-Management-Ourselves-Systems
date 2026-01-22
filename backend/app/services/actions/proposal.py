"""
LLM-powered action proposal service.

Analyzes tasks and suggests appropriate actions.
"""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.logging import logger
from app.services.llm import get_llm_client
from app.services.actions.registry import action_registry


class ActionProposal:
    """Represents a proposed action for a task."""

    def __init__(
        self,
        action_type: str,
        parameters: Dict[str, Any],
        reasoning: str,
        confidence: float = 0.5
    ):
        self.action_type = action_type
        self.parameters = parameters
        self.reasoning = reasoning
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_type": self.action_type,
            "parameters": self.parameters,
            "reasoning": self.reasoning,
            "confidence": self.confidence
        }


class ActionProposalService:
    """Service for proposing actions based on task analysis."""

    SYSTEM_PROMPT = """You are an intelligent task assistant that suggests helpful actions for tasks.

Available actions:
1. send_email: Send an email
   Parameters: to (email), subject (str), body (str), cc (optional), priority (optional)

2. fetch_web_info: Fetch information from a web page
   Parameters: url (str), extract_fields (list, optional)

3. search_web: Search the web for information
   Parameters: query (str), num_results (int, default 5)

4. set_reminder: Set a reminder for the task
   Parameters: remind_at (str, e.g., "1 hour", "tomorrow 9am", "2024-12-25 10:00")

5. calculate: Perform a calculation
   Parameters: expression (str, math expression like "2+2", "sqrt(16)")
   OR
   Parameters: convert_from (str, "100 USD"), convert_to (str, "JPY")

Analyze the task and suggest 0-3 relevant actions. For each action:
- Provide specific parameters (use actual values from the task when possible)
- Explain your reasoning
- Assign a confidence score (0.0-1.0)

Only suggest actions that are clearly helpful and have sufficient information.

Respond in JSON format:
{
  "proposals": [
    {
      "action_type": "action_name",
      "parameters": {...},
      "reasoning": "why this action is helpful",
      "confidence": 0.8
    }
  ]
}

If no actions are appropriate, return {"proposals": []}.
"""

    def __init__(self):
        self.llm_client = get_llm_client()

    async def propose_actions_for_task(
        self,
        task_title: str,
        task_description: Optional[str] = None,
        task_metadata: Optional[Dict[str, Any]] = None
    ) -> List[ActionProposal]:
        """
        Propose actions for a task using LLM analysis.

        Args:
            task_title: The task title
            task_description: Optional detailed description
            task_metadata: Optional metadata (priority, due_date, etc.)

        Returns:
            List of proposed actions
        """
        try:
            # Build user prompt
            user_prompt = self._build_user_prompt(
                task_title, task_description, task_metadata
            )

            logger.info(
                "Requesting action proposals from LLM",
                task_title=task_title
            )

            # Get LLM response
            response = await self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more focused suggestions
                max_tokens=800
            )

            # Parse response
            proposals = self._parse_llm_response(response)

            # Validate proposals
            validated_proposals = []
            for proposal in proposals:
                if self._validate_proposal(proposal):
                    validated_proposals.append(proposal)
                else:
                    logger.warning(
                        "Invalid proposal filtered out",
                        action_type=proposal.action_type
                    )

            logger.info(
                "Action proposals generated",
                task_title=task_title,
                num_proposals=len(validated_proposals)
            )

            return validated_proposals

        except Exception as e:
            logger.error(
                "Error proposing actions",
                task_title=task_title,
                error=str(e)
            )
            return []

    def _build_user_prompt(
        self,
        title: str,
        description: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Build the user prompt for LLM."""
        prompt_parts = [f"Task: {title}"]

        if description:
            prompt_parts.append(f"Description: {description}")

        if metadata:
            if metadata.get("priority"):
                prompt_parts.append(f"Priority: {metadata['priority']}")
            if metadata.get("due_date"):
                prompt_parts.append(f"Due date: {metadata['due_date']}")
            if metadata.get("tags"):
                prompt_parts.append(f"Tags: {', '.join(metadata['tags'])}")

        prompt_parts.append("\nSuggest helpful actions for this task.")

        return "\n".join(prompt_parts)

    def _parse_llm_response(self, response: str) -> List[ActionProposal]:
        """Parse LLM response into ActionProposal objects."""
        try:
            # Extract JSON from response
            response = response.strip()

            # Handle markdown code blocks
            if response.startswith("```"):
                lines = response.split("\n")
                json_lines = []
                in_code = False
                for line in lines:
                    if line.startswith("```"):
                        in_code = not in_code
                    elif in_code:
                        json_lines.append(line)
                response = "\n".join(json_lines)

            data = json.loads(response)
            proposals = []

            for proposal_data in data.get("proposals", []):
                proposal = ActionProposal(
                    action_type=proposal_data["action_type"],
                    parameters=proposal_data["parameters"],
                    reasoning=proposal_data["reasoning"],
                    confidence=proposal_data.get("confidence", 0.5)
                )
                proposals.append(proposal)

            return proposals

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON", error=str(e), response=response)
            return []
        except Exception as e:
            logger.error("Error parsing LLM response", error=str(e))
            return []

    def _validate_proposal(self, proposal: ActionProposal) -> bool:
        """Validate that a proposal is executable."""
        # Check if action type exists
        if not action_registry.has_action(proposal.action_type):
            logger.warning(
                "Unknown action type in proposal",
                action_type=proposal.action_type
            )
            return False

        # Check confidence threshold
        if proposal.confidence < 0.3:
            logger.info(
                "Proposal confidence too low",
                action_type=proposal.action_type,
                confidence=proposal.confidence
            )
            return False

        # Try to instantiate the action to validate parameters
        try:
            executor_class = action_registry.get_executor(proposal.action_type)
            executor = executor_class(proposal.parameters)
            # If no exception, parameters are valid
            return True
        except Exception as e:
            logger.warning(
                "Invalid parameters in proposal",
                action_type=proposal.action_type,
                error=str(e)
            )
            return False

    async def propose_actions_for_multiple_tasks(
        self,
        tasks: List[Dict[str, Any]]
    ) -> Dict[int, List[ActionProposal]]:
        """
        Propose actions for multiple tasks in batch.

        Args:
            tasks: List of task dictionaries with task_id, title, description

        Returns:
            Dictionary mapping task_id to list of proposals
        """
        results = {}

        for task in tasks:
            task_id = task.get("task_id")
            if not task_id:
                continue

            proposals = await self.propose_actions_for_task(
                task_title=task.get("title", ""),
                task_description=task.get("description"),
                task_metadata={
                    "priority": task.get("priority"),
                    "due_date": task.get("due_date"),
                    "tags": task.get("tags", [])
                }
            )

            if proposals:
                results[task_id] = proposals

        return results


# Global instance
proposal_service = ActionProposalService()


async def propose_actions_for_task(
    task_title: str,
    task_description: Optional[str] = None,
    task_metadata: Optional[Dict[str, Any]] = None
) -> List[ActionProposal]:
    """
    Helper function to propose actions for a task.

    Args:
        task_title: The task title
        task_description: Optional detailed description
        task_metadata: Optional metadata

    Returns:
        List of proposed actions
    """
    return await proposal_service.propose_actions_for_task(
        task_title, task_description, task_metadata
    )
