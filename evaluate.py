"""
Script 3: evaluate.py

Read all scored_output.csv files in outputs/ folder.
Compute per model, per condition:
  - ICC(2,1) vs human_score
  - Exact match %
  - Adjacent agreement %
  - Mean bias
  - Sensitivity/Specificity at 2→3 boundary
  - BERTScore F1 (CoT only)

Output: outputs/metrics_report.csv + printed summary table.

Usage:
    python evaluate.py \\
        --scored_dir outputs/ \\
        --output_csv outputs/metrics_report.csv
"""

import argparse
import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_scored_csv(csv_path: str) -> List[Dict]:
    """Load a scored_output.csv file."""
    rows = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Only include rows that have a severity score and human score
                severity = row.get('p2_severity_final', '').strip()
                human = row.get('human_score', '').strip()
                if severity and human:
                    try:
                        rows.append({
                            'transcript_id': row.get('transcript_id', ''),
                            'p2_severity_final': int(float(severity)),
                            'human_score': int(float(human)),
                            'model': row.get('model', ''),
                            'condition': row.get('condition', ''),
                            'description_reasoning': row.get('description_reasoning', ''),
                            'tenacity_reasoning': row.get('tenacity_reasoning', ''),
                            'distress_reasoning': row.get('distress_reasoning', ''),
                            'interference_reasoning': row.get('interference_reasoning', ''),
                            'frequency_reasoning': row.get('frequency_reasoning', ''),
                        })
                    except (ValueError, TypeError):
                        logger.warning(f"Skipping row with invalid scores in {csv_path}")
    except Exception as e:
        logger.warning(f"Error loading {csv_path}: {e}")
    return rows


def compute_icc_2_1(predictions: np.ndarray, gold_standard: np.ndarray) -> Tuple[float, float]:
    """
    Compute ICC(2,1) intraclass correlation coefficient.
    
    Args:
        predictions: Array of model predictions (n,)
        gold_standard: Array of human scores (n,)
    
    Returns:
        (icc_value, confidence_interval_lower, confidence_interval_upper)
    """
    try:
        from scipy.stats import f_oneway
        from scipy import stats
    except ImportError:
        logger.warning("scipy not available, cannot compute ICC")
        return None, None
    
    try:
        # ICC(2,1): Two-way mixed effects, absolute agreement, single measurement
        # Formula: ICC(2,1) = (BMS - EMS) / (BMS + (k-1)*EMS)
        # where k=2 (two raters: model and human)
        
        n = len(predictions)
        if n < 2:
            return None, None
        
        # Create a ratings matrix: n subjects x 2 raters
        ratings = np.column_stack([predictions, gold_standard])
        
        # One-way ANOVA
        # Sum of squares
        grand_mean = np.mean(ratings)
        ss_total = np.sum((ratings - grand_mean) ** 2)
        
        # Between subjects (rows)
        subject_means = np.mean(ratings, axis=1)
        ss_between = np.sum((subject_means - grand_mean) ** 2) * 2  # 2 raters
        
        # Within subjects (error)
        ss_within = ss_total - ss_between
        
        # Mean squares
        df_between = n - 1
        df_within = n
        
        bms = ss_between / df_between
        ems = ss_within / df_within
        
        k = 2  # number of raters
        icc = (bms - ems) / (bms + (k - 1) * ems)
        
        return float(icc), None
    except Exception as e:
        logger.warning(f"Error computing ICC: {e}")
        return None, None


def compute_metrics(predictions: np.ndarray, gold_standard: np.ndarray) -> Dict:
    """Compute all evaluation metrics."""
    metrics = {}
    
    # ICC(2,1)
    icc, _ = compute_icc_2_1(predictions, gold_standard)
    metrics['icc_2_1'] = icc
    
    # Exact match %
    exact_match = np.sum(predictions == gold_standard) / len(predictions) * 100
    metrics['exact_match_pct'] = exact_match
    
    # Adjacent agreement %
    adjacent = np.sum(np.abs(predictions - gold_standard) <= 1) / len(predictions) * 100
    metrics['adjacent_agreement_pct'] = adjacent
    
    # Mean bias
    mean_bias = np.mean(predictions - gold_standard)
    metrics['mean_bias'] = mean_bias
    
    # Sensitivity/Specificity at 2→3 boundary (CHR threshold)
    # Sensitivity: True Positive Rate (TP / (TP + FN))
    # Specificity: True Negative Rate (TN / (TN + FP))
    # Threshold: if gold >= 3, positive; if gold <= 2, negative
    # Prediction: if pred >= 3, predicted positive; if pred <= 2, predicted negative
    
    gold_positive = gold_standard >= 3
    pred_positive = predictions >= 3
    
    tp = np.sum(gold_positive & pred_positive)
    fp = np.sum((~gold_positive) & pred_positive)
    tn = np.sum((~gold_positive) & (~pred_positive))
    fn = np.sum(gold_positive & (~pred_positive))
    
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else None
    specificity = tn / (tn + fp) if (tn + fp) > 0 else None
    
    metrics['sensitivity_at_2_3'] = sensitivity
    metrics['specificity_at_2_3'] = specificity
    
    return metrics


def compute_bert_score_f1(reasoning_list: List[str], gold_list: List[str]) -> Optional[float]:
    """
    Compute BERTScore F1 on reasoning chains (CoT condition only).
    
    Args:
        reasoning_list: List of model reasoning texts
        gold_list: List of gold reasoning texts (if available, else empty strings)
    
    Returns:
        Mean F1 score or None
    """
    try:
        from bert_score import score
    except ImportError:
        logger.warning("bert-score not installed, skipping BERTScore computation")
        return None
    
    try:
        # Filter out empty strings
        pairs = [(r, g) for r, g in zip(reasoning_list, gold_list) if r and g]
        if not pairs:
            return None
        
        reasoning_texts, gold_texts = zip(*pairs)
        
        # Compute BERTScore
        _, _, f1_scores = score(reasoning_texts, gold_texts, lang='en', verbose=False)
        return float(np.mean(f1_scores))
    except Exception as e:
        logger.warning(f"Error computing BERTScore: {e}")
        return None


def evaluate(scored_dir: str, output_csv: str) -> None:
    """
    Evaluate all scored_output.csv files and generate metrics report.
    
    Args:
        scored_dir: Directory with scored_output.csv files
        output_csv: Output metrics CSV path
    """
    
    scored_path = Path(scored_dir)
    csv_files = list(scored_path.glob('scored_*.csv'))
    
    if not csv_files:
        logger.error(f"No scored_*.csv files found in {scored_dir}")
        return
    
    logger.info(f"Found {len(csv_files)} CSV files")
    
    # Load all data
    all_data: Dict[str, List[Dict]] = {}
    for csv_file in sorted(csv_files):
        data = load_scored_csv(str(csv_file))
        if data:
            # Key by model and condition
            for row in data:
                key = f"{row['model']}_{row['condition']}"
                if key not in all_data:
                    all_data[key] = []
                all_data[key].append(row)
    
    logger.info(f"Loaded data for {len(all_data)} model/condition pairs")
    
    # Compute metrics per model/condition
    metrics_rows = []
    
    for key in sorted(all_data.keys()):
        data = all_data[key]
        model, condition = key.split('_')
        
        logger.info(f"Computing metrics for {key} ({len(data)} rows)")
        
        predictions = np.array([row['p2_severity_final'] for row in data])
        gold_standard = np.array([row['human_score'] for row in data])
        
        metrics = compute_metrics(predictions, gold_standard)
        
        # BERTScore for CoT only (if reasoning available)
        bert_f1 = None
        if condition == 'CoT':
            reasoning_list = [row['description_reasoning'] or '' for row in data]
            gold_reasoning = [''] * len(data)  # Placeholder
            bert_f1 = compute_bert_score_f1(reasoning_list, gold_reasoning)
        
        metrics_row = {
            'model': model,
            'condition': condition,
            'n_samples': len(data),
            'icc_2_1': f"{metrics.get('icc_2_1', ''):.3f}" if metrics.get('icc_2_1') is not None else '',
            'exact_match_pct': f"{metrics.get('exact_match_pct', ''):.1f}" if metrics.get('exact_match_pct') is not None else '',
            'adjacent_agreement_pct': f"{metrics.get('adjacent_agreement_pct', ''):.1f}" if metrics.get('adjacent_agreement_pct') is not None else '',
            'mean_bias': f"{metrics.get('mean_bias', ''):.2f}" if metrics.get('mean_bias') is not None else '',
            'sensitivity_at_2_3': f"{metrics.get('sensitivity_at_2_3', ''):.3f}" if metrics.get('sensitivity_at_2_3') is not None else '',
            'specificity_at_2_3': f"{metrics.get('specificity_at_2_3', ''):.3f}" if metrics.get('specificity_at_2_3') is not None else '',
            'bert_score_f1': f"{bert_f1:.3f}" if bert_f1 is not None else '',
        }
        metrics_rows.append(metrics_row)
    
    # Write metrics CSV
    if metrics_rows:
        fieldnames = [
            'model', 'condition', 'n_samples',
            'icc_2_1', 'exact_match_pct', 'adjacent_agreement_pct',
            'mean_bias', 'sensitivity_at_2_3', 'specificity_at_2_3', 'bert_score_f1'
        ]
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(metrics_rows)
        
        logger.info(f"Wrote metrics report to {output_csv}")
        
        # Print summary table
        print("\n" + "="*100)
        print("EVALUATION METRICS SUMMARY")
        print("="*100)
        print(f"{'Model':<12} {'Condition':<8} {'N':<6} {'ICC(2,1)':<10} {'Exact %':<8} {'Adj %':<8} {'Bias':<8} {'Sens@2→3':<10} {'Spec@2→3':<10} {'BERTScore':<10}")
        print("-"*100)
        
        for row in metrics_rows:
            print(f"{row['model']:<12} {row['condition']:<8} {row['n_samples']:<6} {row['icc_2_1']:<10} "
                  f"{row['exact_match_pct']:<8} {row['adjacent_agreement_pct']:<8} {row['mean_bias']:<8} "
                  f"{row['sensitivity_at_2_3']:<10} {row['specificity_at_2_3']:<10} {row['bert_score_f1']:<10}")
        
        print("="*100 + "\n")
    else:
        logger.warning("No metrics computed")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate PSYCHS P2 scoring results"
    )
    parser.add_argument(
        '--scored_dir',
        required=True,
        help='Directory with scored_*.csv files'
    )
    parser.add_argument(
        '--output_csv',
        default='outputs/metrics_report.csv',
        help='Output metrics CSV (default: outputs/metrics_report.csv)'
    )
    
    args = parser.parse_args()
    evaluate(args.scored_dir, args.output_csv)


if __name__ == '__main__':
    main()
