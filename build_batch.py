"""
Script 1: build_batch.py

Read all .txt and .json transcripts from input_dir → batch_input.csv.
Resume-safe: skip files already in output by content_hash.

Usage:
    python build_batch.py \\
        --input_dir /path/to/p2_extracted_transcripts \\
        --output_csv data/batch_input.csv \\
        --gold_csv /path/to/human_scores.csv
"""

import argparse
import os
import json
import csv
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_text_and_id_from_json(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract text and interview ID from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Try text field extraction
        text = None
        for key in ['transcript', 'text', 'content', 'body', 'response']:
            if key in data and isinstance(data[key], str):
                text = data[key]
                break
        
        # Try ID field extraction
        interview_id = None
        for key in ['interview_id', 'participant_id', 'subject_id', 'id']:
            if key in data:
                interview_id = str(data[key])
                break
        
        # Fallback ID: filename stem
        if not interview_id:
            interview_id = Path(file_path).stem
        
        return text, interview_id
    except Exception as e:
        logger.warning(f"Error reading JSON {file_path}: {e}")
        return None, None


def extract_text_and_id_from_txt(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract text from .txt file. ID is filename stem."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        interview_id = Path(file_path).stem
        return text, interview_id
    except Exception as e:
        logger.warning(f"Error reading TXT {file_path}: {e}")
        return None, None


def compute_content_hash(text: str) -> str:
    """Compute MD5 hash (first 8 chars) of text."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]


def compute_qaqc_flags(text: Optional[str], interview_id: Optional[str]) -> str:
    """Compute QA/QC flags. Return 'OK' or pipe-separated flags."""
    flags = []
    
    if not text:
        flags.append("EMPTY_TEXT")
    else:
        if len(text) < 50:
            flags.append("TEXT_TOO_SHORT")
        if len(text) > 15000:
            flags.append("TEXT_VERY_LONG")
    
    if not interview_id:
        flags.append("MISSING_ID")
    
    return "|".join(flags) if flags else "OK"


def load_gold_scores(gold_csv_path: str) -> Dict[str, float]:
    """Load human scores from CSV. Expected columns: transcript_id, human_score."""
    gold_scores = {}
    try:
        with open(gold_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tid = row.get('transcript_id') or row.get('id')
                score = row.get('human_score') or row.get('score')
                if tid and score:
                    try:
                        gold_scores[tid] = float(score)
                    except ValueError:
                        pass
        logger.info(f"Loaded {len(gold_scores)} gold scores from {gold_csv_path}")
    except Exception as e:
        logger.warning(f"Error loading gold CSV: {e}")
    return gold_scores


def load_existing_hashes(output_csv_path: str) -> set:
    """Load existing content hashes from output CSV (for resume safety)."""
    existing_hashes = set()
    if os.path.exists(output_csv_path):
        try:
            with open(output_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    h = row.get('content_hash')
                    if h:
                        existing_hashes.add(h)
            logger.info(f"Found {len(existing_hashes)} existing rows in {output_csv_path}")
        except Exception as e:
            logger.warning(f"Error loading existing output: {e}")
    return existing_hashes


def build_batch(
    input_dir: str,
    output_csv: str,
    gold_csv: Optional[str] = None,
) -> None:
    """
    Build batch input CSV from all transcripts in input_dir.
    
    Args:
        input_dir: Folder with .txt/.json transcripts
        output_csv: Output CSV path
        gold_csv: Optional CSV with human scores
    """
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(output_csv) or '.', exist_ok=True)
    
    # Load existing hashes for resume safety
    existing_hashes = load_existing_hashes(output_csv)
    
    # Load gold scores if provided
    gold_scores = {}
    if gold_csv:
        gold_scores = load_gold_scores(gold_csv)
    
    # Collect all transcript files
    input_path = Path(input_dir)
    transcript_files = list(input_path.glob('*.txt')) + list(input_path.glob('*.json'))
    transcript_files.sort()
    
    logger.info(f"Found {len(transcript_files)} transcript files in {input_dir}")
    
    rows = []
    row_id = 1
    
    for file_path in transcript_files:
        # Extract text and ID based on file type
        if file_path.suffix == '.json':
            text, interview_id = extract_text_and_id_from_json(str(file_path))
        else:  # .txt
            text, interview_id = extract_text_and_id_from_txt(str(file_path))
        
        if not text:
            logger.warning(f"Skipping {file_path}: no text extracted")
            continue
        
        # Compute hash for resume safety
        content_hash = compute_content_hash(text)
        if content_hash in existing_hashes:
            logger.info(f"Skipping {file_path}: already processed (hash {content_hash})")
            continue
        
        # Compute QA/QC flags
        qaqc_flags = compute_qaqc_flags(text, interview_id)
        
        # Get human score if available
        human_score = gold_scores.get(interview_id) if interview_id else None
        
        row = {
            'row_id': row_id,
            'transcript_id': interview_id or '',
            'source_file': file_path.name,
            'file_type': file_path.suffix[1:],  # 'txt' or 'json'
            'text_length': len(text),
            'content_hash': content_hash,
            'transcript': text,
            'human_score': human_score if human_score is not None else '',
            'qaqc_flags': qaqc_flags,
        }
        rows.append(row)
        row_id += 1
    
    # Write output CSV
    if rows:
        fieldnames = [
            'row_id', 'transcript_id', 'source_file', 'file_type', 'text_length',
            'content_hash', 'transcript', 'human_score', 'qaqc_flags'
        ]
        
        # Check if file exists to decide on write mode
        file_exists = os.path.exists(output_csv)
        
        with open(output_csv, 'a' if file_exists else 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows)
        
        logger.info(f"Wrote {len(rows)} new rows to {output_csv}")
    else:
        logger.warning("No new transcripts to write")


def main():
    parser = argparse.ArgumentParser(
        description="Build batch input CSV from transcripts"
    )
    parser.add_argument(
        '--input_dir',
        required=True,
        help='Folder with .txt/.json transcripts'
    )
    parser.add_argument(
        '--output_csv',
        default='data/batch_input.csv',
        help='Output CSV path (default: data/batch_input.csv)'
    )
    parser.add_argument(
        '--gold_csv',
        default=None,
        help='Optional CSV with [transcript_id, human_score]'
    )
    
    args = parser.parse_args()
    
    build_batch(
        input_dir=args.input_dir,
        output_csv=args.output_csv,
        gold_csv=args.gold_csv,
    )


if __name__ == '__main__':
    main()
