"""Abstract base class for LLM backends."""

from abc import ABC, abstractmethod


class LLMBackend(ABC):
    """Abstract base class for LLM backends.
    
    All backends must implement the generate() method to return the LLM response text.
    """
    
    @abstractmethod
    def generate(self, prompt_system: str, prompt_user: str) -> str:
        """
        Generate LLM response given system and user prompts.
        
        Args:
            prompt_system (str): System prompt / instructions
            prompt_user (str): User message / query
        
        Returns:
            str: Raw text response from the model (may include reasoning, then JSON)
        """
        pass
