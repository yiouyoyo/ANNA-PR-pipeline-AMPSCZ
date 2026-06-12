"""
Script 2: run_scoring.py

Read batch_input.csv → run 8-step chain per transcript → scored_output.csv.

Resume-safe: flush after every row, skip rows with non-null p2_severity_final on re-run.

Usage:
    python run_scoring.py \\
        --input_csv data/batch_input.csv \\
        --output_csv outputs/scored_llama_ZS.csv \\
        --model llama \\
        --model_name meta-llama/Llama-3.3-70B-Instruct \\
        --condition ZS \\
        --gpu_id 0 \\
        --temperature 0.0 \\
        --max_tokens 512
"""

import argparse
import os
import csv
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_llm_backend(
    model: str,
    model_name: str,
    gpu_id: int,
    gpu_memory_utilization: float,
    max_model_len: Optional[int],
    temperature: float,
    max_tokens: int,
):
    """Instantiate the appropriate LLM backend."""
    if model == 'gptoss':
        from models.gptoss import GPTOSSBackend
        return GPTOSSBackend(
            model_name=model_name,
            gpu_id=gpu_id,
            gpu_memory_utilization=gpu_memory_utilization,
            max_model_len=max_model_len,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif model in ['llama', 'gemma']:
        from models.vllm_standard import VLLMStandardBackend
        return VLLMStandardBackend(
            model_name=model_name,
            gpu_id=gpu_id,
            gpu_memory_utilization=gpu_memory_utilization,
            max_model_len=max_model_len,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        raise ValueError(f"Unknown model: {model}")


def load_existing_scores(output_csv: str) -> set:
    """Load row IDs that have already been scored (resume safety)."""
    scored_row_ids = set()
    if os.path.exists(output_csv):
        try:
            with open(output_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # If p2_severity_final is not null, row was already scored
                    severity = row.get('p2_severity_final', '').strip()
                    if severity and severity != '':
                        row_id = row.get('row_id', '').strip()
                        if row_id:
                            scored_row_ids.add(row_id)
            logger.info(f"Found {len(scored_row_ids)} already-scored rows in {output_csv}")
        except Exception as e:
            logger.warning(f"Error loading existing output: {e}")
    return scored_row_ids


def run_scoring(
    input_csv: str,
    output_csv: str,
    model: str,
    model_name: str,
    condition: str,
    gpu_id: int = 0,
    gpu_memory_utilization: float = 0.85,
    max_model_len: Optional[int] = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    dry_run: bool = False,
    skip_flagged: bool = False,
    batch_size: int = 10,
    sleep_sec: float = 1.0,
) -> None:
    """
    Run 8-step chained scoring on all transcripts in input_csv.
    
    Args:
        input_csv: Path to batch_input.csv
        output_csv: Output scored_output.csv path
        model: 'gptoss' | 'llama' | 'gemma'
        model_name: Full HuggingFace model ID
        condition: 'ZS' | 'FS' | 'CoT'
        gpu_id: CUDA device ID
        gpu_memory_utilization: vLLM GPU memory fraction (0-1)
        max_model_len: Optional maximum model length
        temperature: Sampling temperature (should be 0.0 for scoring)
        max_tokens: Maximum tokens per response
        dry_run: Run without LLM calls, use mock scores
        skip_flagged: Skip rows where qaqc_flags != 'OK'
        batch_size: Not used in current implementation (kept for CLI compatibility)
        sleep_sec: Sleep between rows (for GPU cooling, etc.)
    """
    
    logger.info(f"Starting scoring run: model={model}, condition={condition}, dry_run={dry_run}")
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(output_csv) or '.', exist_ok=True)
    
    # Instantiate LLM backend (unless dry_run)
    llm_backend = None
    if not dry_run:
        llm_backend = get_llm_backend(
            model=model,
            model_name=model_name,
            gpu_id=gpu_id,
            gpu_memory_utilization=gpu_memory_utilization,
            max_model_len=max_model_len,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    # Load already-scored rows (for resume safety)
    scored_row_ids = load_existing_scores(output_csv)
    
    # Read input CSV
    rows_to_score = []
    try:
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_id = row.get('row_id', '').strip()
                if row_id in scored_row_ids:
                    logger.debug(f"Skipping already-scored row {row_id}")
                    continue
                rows_to_score.append(row)
    except Exception as e:
        logger.error(f"Error reading input CSV: {e}")
        return
    
    logger.info(f"Found {len(rows_to_score)} rows to score")
    
    # Define output fieldnames
    fieldnames = [
        'row_id', 'transcript_id', 'source_file', 'human_score',
        'model', 'condition', 'llm_calls', 'error',
        'suspicious_content_present', 'screening_evidence',
        'description_score', 'supporting_evidence', 'disconfirming_evidence', 'description_reasoning',
        'tenacity_score', 'doubt_expressed', 'doubt_source', 'tenacity_reasoning',
        'synthesis_path', 'tiebreaker_needed',
        'distress_score', 'distress_evidence', 'distress_cause_confirmed', 'distress_reasoning',
        'interference_score', 'behavioral_change', 'social_impact', 'interference_reasoning',
        'p2_severity_final', 'synthesis_rule_applied', 'secondary_used',
        'frequency_pm_score', 'frequency_lt_py_score', 'frequency_evidence', 'frequency_reasoning',
        'lifetime_psychosis', 'sips_bips', 'sips_apss',
        'caarms_blips', 'caarms_subthreshold_frequency', 'caarms_subthreshold_intensity',
        'scored_at',
    ]
    
    # Check if output file exists
    file_exists = os.path.exists(output_csv)
    
    # Process each row
    for idx, input_row in enumerate(rows_to_score, 1):
        row_id = input_row.get('row_id', '').strip()
        transcript_id = input_row.get('transcript_id', '').strip()
        transcript = input_row.get('transcript', '').strip()
        human_score = input_row.get('human_score', '').strip()
        qaqc_flags = input_row.get('qaqc_flags', 'OK').strip()
        
        logger.info(f"[{idx}/{len(rows_to_score)}] Scoring row {row_id} ({transcript_id})")
        
        # Skip if flagged and skip_flagged enabled
        if skip_flagged and qaqc_flags != 'OK':
            logger.info(f"  Skipping flagged row (qaqc_flags={qaqc_flags})")
            continue
        
        # Run scoring or use mock
        if dry_run:
            score_result = _generate_mock_score_result(transcript_id)
        else:
            from scoring.chain import score_transcript
            score_result = score_transcript(transcript, llm_backend, condition)
        
        # Build output row
        output_row = {
            'row_id': row_id,
            'transcript_id': transcript_id,
            'source_file': input_row.get('source_file', ''),
            'human_score': human_score,
            'model': model,
            'condition': condition,
            'llm_calls': score_result.get('llm_calls', 0),
            'error': score_result.get('error', ''),
            'suspicious_content_present': score_result.get('suspicious_content_present', ''),
            'screening_evidence': score_result.get('screening_evidence', ''),
            'description_score': score_result.get('description_score', ''),
            'supporting_evidence': score_result.get('supporting_evidence', ''),
            'disconfirming_evidence': score_result.get('disconfirming_evidence', ''),
            'description_reasoning': score_result.get('description_reasoning', ''),
            'tenacity_score': score_result.get('tenacity_score', ''),
            'doubt_expressed': score_result.get('doubt_expressed', ''),
            'doubt_source': score_result.get('doubt_source', ''),
            'tenacity_reasoning': score_result.get('tenacity_reasoning', ''),
            'synthesis_path': score_result.get('synthesis_path', ''),
            'tiebreaker_needed': score_result.get('tiebreaker_needed', ''),
            'distress_score': score_result.get('distress_score', ''),
            'distress_evidence': score_result.get('distress_evidence', ''),
            'distress_cause_confirmed': score_result.get('distress_cause_confirmed', ''),
            'distress_reasoning': score_result.get('distress_reasoning', ''),
            'interference_score': score_result.get('interference_score', ''),
            'behavioral_change': score_result.get('behavioral_change', ''),
            'social_impact': score_result.get('social_impact', ''),
            'interference_reasoning': score_result.get('interference_reasoning', ''),
            'p2_severity_final': score_result.get('p2_severity_final', ''),
            'synthesis_rule_applied': score_result.get('synthesis_rule_applied', ''),
            'secondary_used': score_result.get('secondary_used', ''),
            'frequency_pm_score': score_result.get('frequency_pm_score', ''),
            'frequency_lt_py_score': score_result.get('frequency_lt_py_score', ''),
            'frequency_evidence': score_result.get('frequency_evidence', ''),
            'frequency_reasoning': score_result.get('frequency_reasoning', ''),
            'lifetime_psychosis': score_result.get('lifetime_psychosis', ''),
            'sips_bips': score_result.get('sips_bips', ''),
            'sips_apss': score_result.get('sips_apss', ''),
            'caarms_blips': score_result.get('caarms_blips', ''),
            'caarms_subthreshold_frequency': score_result.get('caarms_subthreshold_frequency', ''),
            'caarms_subthreshold_intensity': score_result.get('caarms_subthreshold_intensity', ''),
            'scored_at': datetime.now().isoformat(),
        }
        
        # Write output row (flush after each row for resume safety)
        with open(output_csv, 'a' if file_exists else 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
                file_exists = True
            writer.writerow(output_row)
        
        logger.info(f"  Wrote row {row_id} to {output_csv}")
        
        # Sleep to allow GPU cooling
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    
    logger.info("Scoring run complete")


def _generate_mock_score_result(transcript_id: str) -> Dict[str, Any]:
    """Generate mock scoring result for dry-run mode."""
    return {
        'suspicious_content_present': True,
        'screening_evidence': 'Mock evidence',
        'description_score': 3,
        'supporting_evidence': 'Mock supporting',
        'disconfirming_evidence': 'Mock disconfirming',
        'description_reasoning': 'Mock reasoning',
        'tenacity_score': 2,
        'doubt_expressed': True,
        'doubt_source': 'when_asked',
        'tenacity_reasoning': 'Mock tenacity reasoning',
        'synthesis_path': 'D=3, T=2, diff=1',
        'tiebreaker_needed': False,
        'distress_score': None,
        'distress_evidence': None,
        'distress_cause_confirmed': None,
        'distress_reasoning': None,
        'interference_score': None,
        'behavioral_change': None,
        'social_impact': None,
        'interference_reasoning': None,
        'p2_severity_final': 2,
        'synthesis_rule_applied': 'adjacent_lower',
        'secondary_used': False,
        'frequency_pm_score': 1,
        'frequency_lt_py_score': 2,
        'frequency_evidence': 'Mock frequency evidence',
        'frequency_reasoning': 'Mock frequency reasoning',
        'lifetime_psychosis': False,
        'sips_bips': False,
        'sips_apss': False,
        'caarms_blips': False,
        'caarms_subthreshold_frequency': False,
        'caarms_subthreshold_intensity': False,
        'llm_calls': 0,
        'error': None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run 8-step chained PSYCHS P2 scoring on transcripts"
    )
    parser.add_argument(
        '--input_csv',
        required=True,
        help='Path to batch_input.csv'
    )
    parser.add_argument(
        '--output_csv',
        default='outputs/scored_output.csv',
        help='Output CSV path (default: outputs/scored_output.csv)'
    )
    parser.add_argument(
        '--model',
        required=True,
        choices=['gptoss', 'llama', 'gemma'],
        help='Model backend'
    )
    parser.add_argument(
        '--model_name',
        default='meta-llama/Llama-3.3-70B-Instruct',
        help='HuggingFace model ID'
    )
    parser.add_argument(
        '--condition',
        required=True,
        choices=['ZS', 'FS', 'CoT'],
        help='Prompting condition: ZS (zero-shot), FS (few-shot), CoT (chain-of-thought)'
    )
    parser.add_argument(
        '--gpu_id',
        type=int,
        default=0,
        help='CUDA device ID (default: 0)'
    )
    parser.add_argument(
        '--gpu_memory_utilization',
        type=float,
        default=0.85,
        help='GPU memory utilization fraction (default: 0.85)'
    )
    parser.add_argument(
        '--max_model_len',
        type=int,
        default=None,
        help='Maximum model length (optional)'
    )
    parser.add_argument(
        '--temperature',
        type=float,
        default=0.0,
        help='Sampling temperature (default: 0.0, must be 0 for deterministic scoring)'
    )
    parser.add_argument(
        '--max_tokens',
        type=int,
        default=512,
        help='Maximum tokens per response (default: 512; use 1500 for CoT)'
    )
    parser.add_argument(
        '--dry_run',
        action='store_true',
        help='Run without LLM calls, use mock scores'
    )
    parser.add_argument(
        '--skip_flagged',
        action='store_true',
        help='Skip rows where qaqc_flags != OK'
    )
    parser.add_argument(
        '--batch_size',
        type=int,
        default=10,
        help='Batch size (default: 10)'
    )
    parser.add_argument(
        '--sleep_sec',
        type=float,
        default=1.0,
        help='Sleep seconds between rows (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    run_scoring(
        input_csv=args.input_csv,
        output_csv=args.output_csv,
        model=args.model,
        model_name=args.model_name,
        condition=args.condition,
        gpu_id=args.gpu_id,
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_model_len=args.max_model_len,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        dry_run=args.dry_run,
        skip_flagged=args.skip_flagged,
        batch_size=args.batch_size,
        sleep_sec=args.sleep_sec,
    )


if __name__ == '__main__':
    main()
