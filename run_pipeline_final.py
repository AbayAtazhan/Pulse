import os
import json
import logging
import argparse
from typing import List, Dict, Any

from run_pipeline_v1 import (
    check_and_prepare_data, 
    calculate_metrics, 
    mock_agent_loop
)
from src.state_freezer.state_freezer import MatchStateFreezer
from src.agent.agent_loop import run_agent_loop
from src.evaluation.grader_baseline import grade_predictions, calculate_naive_baseline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def analyze_update_consistency(
    match_data: Dict[str, Any],
    predictions_by_min: Dict[int, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    home_team = match_data["home_team"]
    away_team = match_data["away_team"]
    events = match_data["events"]
    
    transitions = [
        {"t1": 20, "t2": 45},
        {"t1": 45, "t2": 70}
    ]
    
    results = []
    
    for trans in transitions:
        t1, t2 = trans["t1"], trans["t2"]
        pred1 = predictions_by_min.get(t1)
        pred2 = predictions_by_min.get(t2)
        
        if not pred1 or not pred2 or not pred1.get("is_gradable") or not pred2.get("is_gradable"):
            continue
            
        home_goals = 0
        away_goals = 0
        home_reds = 0
        away_reds = 0
        
        for e in events:
            minute = e.get("minute", 0)
            if t1 < minute <= t2:
                etype = e.get("type")
                team = e.get("team")
                details = str(e.get("details", "")).lower()
                
                if etype == "Goal":
                    if team == home_team:
                        home_goals += 1
                    elif team == away_team:
                        away_goals += 1
                elif etype == "Card" and ("red" in details or "second yellow" in details):
                    if team == home_team:
                        home_reds += 1
                    elif team == away_team:
                        away_reds += 1
                        
        def get_home_win_score(pred):
            res = pred.get("final_result")
            conf = pred.get("final_result_confidence", 0.0)
            if res == "home_win":
                return conf
            elif res == "away_win":
                return -conf
            else:
                return 0.0
                
        score1 = get_home_win_score(pred1)
        score2 = get_home_win_score(pred2)
        shift = score2 - score1
        
        is_sensible = True
        reason = "No critical events in interval"
        
        if home_goals > away_goals and home_reds == 0 and away_reds == 0:
            is_sensible = shift > 0
            reason = f"Home scored {home_goals} goal(s). Win score shifted from {score1:.2f} to {score2:.2f} (diff: {shift:+.2f})."
        elif away_goals > home_goals and home_reds == 0 and away_reds == 0:
            is_sensible = shift < 0
            reason = f"Away scored {away_goals} goal(s). Win score shifted from {score1:.2f} to {score2:.2f} (diff: {shift:+.2f})."
        elif home_reds > 0 and away_reds == 0:
            is_sensible = shift < 0
            reason = f"Home received a red card. Win score shifted from {score1:.2f} to {score2:.2f} (diff: {shift:+.2f})."
        elif away_reds > 0 and home_reds == 0:
            is_sensible = shift > 0
            reason = f"Away received a red card. Win score shifted from {score1:.2f} to {score2:.2f} (diff: {shift:+.2f})."
            
        results.append({
            "transition": f"{t1}->{t2}",
            "critical_events": {
                "home_goals": home_goals,
                "away_goals": away_goals,
                "home_reds": home_reds,
                "away_reds": away_reds
            },
            "shift": round(shift, 3),
            "is_sensible": is_sensible,
            "reason": reason,
            "reads": {
                "t1_read": pred1.get("situational_read"),
                "t2_read": pred2.get("situational_read")
            }
        })
        
    return results


def run_model_pipeline(model_name: str, match_files: List[str], freezer: MatchStateFreezer, dry_run: bool) -> Dict[str, Any]:
    raw_records = []
    too_vague_count = 0
    freeze_minutes = [20, 45, 70]
    
    match_predictions = {}
    
    for idx, match_file in enumerate(match_files):
        with open(match_file, "r", encoding="utf-8") as f:
            match_data = json.load(f)
            
        match_id = match_data["match_id"]
        match_predictions[match_id] = {}
        
        for min_t in freeze_minutes:
            try:
                frozen_state = freezer.freeze(match_data, min_t)
            except ValueError as e:
                logging.error(f"Leakage validation error: {e}")
                continue
                
            if dry_run:
                predictions = mock_agent_loop(frozen_state)
            else:
                try:
                    predictions = run_agent_loop(frozen_state, model_name=model_name)
                except Exception as e:
                    logging.error(f"Failed to query {model_name} for match {match_id} at {min_t}: {e}")
                    continue
                    
            real_continuation = [e for e in match_data["events"] if e["minute"] > min_t]
            
            grades = grade_predictions(
                predictions=predictions,
                real_continuation=real_continuation,
                home_team=frozen_state["home_team"],
                away_team=frozen_state["away_team"],
                frozen_score=frozen_state["score"]
            )
            
            if not predictions.get("is_gradable", True):
                too_vague_count += 1
                
            baseline = calculate_naive_baseline(frozen_state)
            baseline_correct = 1 if baseline["final_result"] == grades.get("actual", {}).get("final_result") else 0
            
            record = {
                "match_id": match_id,
                "freeze_minute": min_t,
                "predictions": predictions,
                "grades": grades,
                "baseline_correct": baseline_correct
            }
            raw_records.append(record)
            
            match_predictions[match_id][min_t] = predictions

    metrics = calculate_metrics(raw_records)
    
    update_test_results = []
    for match_file in match_files:
        with open(match_file, "r", encoding="utf-8") as f:
            match_data = json.load(f)
        match_id = match_data["match_id"]
        
        preds = match_predictions.get(match_id, {})
        if len(preds) == 3:
            updates = analyze_update_consistency(match_data, preds)
            if updates:
                update_test_results.append({
                    "match_id": match_id,
                    "home_team": match_data["home_team"],
                    "away_team": match_data["away_team"],
                    "updates": updates
                })
                
    sensible_count = 0
    total_updates = 0
    for match_res in update_test_results:
        for u in match_res["updates"]:
            if u["reason"] != "No critical events in interval":
                total_updates += 1
                if u["is_sensible"]:
                    sensible_count += 1
                    
    update_consistency_ratio = (sensible_count / total_updates) if total_updates > 0 else 1.0

    return {
        "model_name": model_name,
        "too_vague_count": too_vague_count,
        "metrics": metrics,
        "update_test": {
            "consistency_ratio": round(update_consistency_ratio, 3),
            "total_significant_updates": total_updates,
            "sensible_updates_count": sensible_count,
            "raw_update_runs": update_test_results
        },
        "raw_records": raw_records
    }


def main():
    parser = argparse.ArgumentParser(description="Pulse Final Evaluation Pipeline")
    parser.add_argument("--model1", type=str, default="qwen3.6-27b", help="Model 1 Name")
    parser.add_argument("--model2", type=str, default="gemma-4-31b", help="Model 2 Name")
    parser.add_argument("--matches", type=int, default=20, help="Number of matches")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    logging.info(f"Starting FINAL comparison pipeline. Matches={args.matches}, Dry-run={args.dry_run}")
    
    check_and_prepare_data(target_count=args.matches)
    
    processed_dir = "data/processed"
    match_files = [os.path.join(processed_dir, f) for f in os.listdir(processed_dir) if f.endswith(".json")]
    match_files = match_files[:args.matches]
    
    freezer = MatchStateFreezer(data_dir=processed_dir)
    
    logging.info(f"=== RUNNING PIPELINE FOR MODEL 1: {args.model1} ===")
    results_m1 = run_model_pipeline(args.model1, match_files, freezer, args.dry_run)
    
    logging.info(f"=== RUNNING PIPELINE FOR MODEL 2: {args.model2} ===")
    results_m2 = run_model_pipeline(args.model2, match_files, freezer, args.dry_run)
    
    comparison_data = {
        "model_1": results_m1,
        "model_2": results_m2
    }
    
    output_file = "final_comparison.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(comparison_data, f, ensure_ascii=False, indent=4)
        
    logging.info("=" * 60)
    logging.info(f"Final comparison completed. Results saved to {output_file}")
    logging.info("=" * 60)


if __name__ == "__main__":
    main()
