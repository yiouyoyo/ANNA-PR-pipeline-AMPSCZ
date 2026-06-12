"""Standard vLLM backend for Llama 3.3 and Gemma models."""

import os
import logging
from typing import Optional

from models.base import LLMBackend

logger = logging.getLogger(__name__)


class VLLMStandardBackend(LLMBackend):
    """
    Standard vLLM backend for Llama 3.3-70B, Gemma 3-27B, and similar models.
    
    Requires: vllm >= 0.4.0
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
        Initialize vLLM backend.
        
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
        except ImportError as e:
            raise ImportError(
                "vLLM backend requires vllm package. "
                "Install with: pip install vllm"
            ) from e
        
        os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
        os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
        
        logger.info(f"Initializing vLLM backend: {model_name} on GPU {gpu_id}")
        
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
        self.tokenizer = self.llm.get_tokenizer()
        self.sampling = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        logger.info("vLLM backend initialized successfully")
    
    def generate(self, prompt_system: str, prompt_user: str) -> str:
        """
        Generate response using vLLM with standard chat template.
        
        Args:
            prompt_system: System prompt
            prompt_user: User message
        
        Returns:
            str: Raw response text
        """
        try:
            messages = [
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": prompt_user},
            ]
            prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            output = self.llm.generate([prompt], self.sampling)
            return output[0].outputs[0].text if output[0].outputs else ''
        except Exception as e:
            logger.error(f"Error in vLLM generation: {e}")
            return ""
