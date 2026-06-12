"""GPT-OSS backend via Harmony encoding and vLLM."""

import os
import logging
from typing import Optional

from models.base import LLMBackend

logger = logging.getLogger(__name__)


class GPTOSSBackend(LLMBackend):
    """
    GPT-OSS backend using Harmony encoding and vLLM.
    
    Requires: vllm, openai_harmony packages
    Lab-specific: adapt build_harmony_conversation() signature as needed.
    """
    
    def __init__(
        self,
        model_name: str,
        gpu_id: int = 0,
        gpu_memory_utilization: float = 0.85,
        max_model_len: Optional[int] = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ):
        """
        Initialize GPT-OSS backend.
        
        Args:
            model_name: HuggingFace model ID or local path
            gpu_id: CUDA device ID
            gpu_memory_utilization: vLLM GPU memory utilization (0-1)
            max_model_len: Maximum model length (optional)
            temperature: Sampling temperature (default 0.0)
            max_tokens: Maximum tokens per response
        """
        try:
            from vllm import LLM, SamplingParams
            from openai_harmony import HarmonyEncodingName, Role, load_harmony_encoding
        except ImportError as e:
            raise ImportError(
                "GPT-OSS backend requires vllm and openai_harmony. "
                "Install with: pip install vllm openai_harmony"
            ) from e
        
        os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
        os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
        
        logger.info(f"Initializing GPT-OSS backend: {model_name} on GPU {gpu_id}")
        
        llm_kwargs = {
            'model': model_name,
            'enable_prefix_caching': True,
            'tensor_parallel_size': 1,
            'gpu_memory_utilization': gpu_memory_utilization,
            'dtype': 'auto',
            'trust_remote_code': True,
        }
        if max_model_len:
            llm_kwargs['max_model_len'] = max_model_len
        
        self.llm = LLM(**llm_kwargs)
        self.encoding = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        self.stop_token_ids = self.encoding.stop_tokens_for_assistant_actions()
        self.sampling = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            stop_token_ids=self.stop_token_ids,
        )
        
        logger.info("GPT-OSS backend initialized successfully")
    
    def generate(self, prompt_system: str, prompt_user: str) -> str:
        """
        Generate response using GPT-OSS with Harmony encoding.
        
        Args:
            prompt_system: System prompt
            prompt_user: User message
        
        Returns:
            str: Raw response text
        """
        try:
            # NOTE: Adapt build_harmony_conversation() call to match lab codebase signature
            # This is a placeholder — replace with actual function from your lab infrastructure
            conversation = _build_harmony_conversation(system=prompt_system, user=prompt_user)
            
            from openai_harmony import Role
            token_ids = self.encoding.render_conversation_for_completion(
                conversation, Role.ASSISTANT
            )
            output = self.llm.generate(
                [{'prompt_token_ids': token_ids}],
                self.sampling
            )
            return output[0].outputs[0].text if output[0].outputs else ''
        except Exception as e:
            logger.error(f"Error in GPT-OSS generation: {e}")
            return ""


def _build_harmony_conversation(system: str, user: str):
    """
    Build Harmony conversation format.
    
    NOTE: This is a placeholder. Replace with the actual function from your lab's
    openai_harmony implementation to match the exact signature and message format.
    """
    from openai_harmony import Role, MessageRole
    
    return [
        {"role": Role.SYSTEM, "content": system},
        {"role": Role.USER, "content": user},
    ]
