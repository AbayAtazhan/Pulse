import os
import json
import logging
import argparse
from typing import List, Dict, Any

from src.data_ingestion.statsbomb_parser import StatsBombParser
from src.state_freezer.state_freezer import MatchStateFreezer
from src.agent.agent_loop import run_agent_loop
from src.evaluation.grader_baseline import grade_predictions, calculate_naive_baseline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def mock_agent_loop(frozen_state: Dict[str, Any]) -> Dict[str, Any]:
    import random
    home_team = frozen_state["home_team"]
    away_team = frozen_state["away_team"]
    
    score = frozen_state["score"]
    home_score = score.get("home", 0) if isinstance(score, dict) else int(score.split("-")[0])
    away_score = score.get("away", 0) if isinstance(score, dict) else int(score.split("-")[1])
    
    if home_score > away_score:
        result = "home_win"
    elif home_score < away_score:
        result = "away_win"
    else:
        result = random.choice(["home_win", "away_win", "draw"])
        
    return {
        "situational_read": f"MOCK: {home_team} vs {away_team}. Score {home_score}-{away_score}.",
        "next_goal": random.choice(["home", "away", "no_more_goals"]),
        "next_goal_confidence": round(random.uniform(0.1, 0.95), 2),
        "final_result": result,
        "final_result_confidence": round(random.uniform(0.3, 0.99), 2),
        "next_clear_chance": random.choice(["home", "away"]),
        "next_clear_chance_confidence": round(random.uniform(0.2, 0.95), 2),
        "is_gradable": True
    }


def check_and_prepare_data(target_count: int = 20):
    processed_dir = "data/processed"
    os.makedirs(processed_dir, exist_ok=True)
    existing_files = [f for f in os.listdir(processed_dir) if f.endswith(".json")]
    
    if len(existing_files) < target_count:
        needed = target_count - len(existing_files)
        logging.info(f"Found only {len(existing_files)} processed matches. Downloading {needed} more...")
        parser = StatsBombParser(output_dir=processed_dir)
        try:
            match_ids = parser.fetch_matches(competition_id=43, season_id=106)
            processed_ids = {int(f.split(".")[0]) for f in existing_files if f.split(".")[0].isdigit()}
            to_process = [m_id for m_id in match_ids if m_id not in processed_ids]
            
            for m_id in to_process[:needed]:
                logging.info(f"Downloading and parsing match {m_id}...")
                data = parser.extract_match_events(m_id)
                parser.save_match_data(data)
        except Exception as e:
            logging.error(f"Error during data preparation: {e}")


def run_pipeline(model_name: str, num_matches: int, dry_run: bool):
    check_and_prepare_data(target_count=num_matches)
    
    processed_dir = "data/processed"
    match_files = [os.path.join(processed_dir, f) for f in os.listdir(processed_dir) if f.endswith(".json")]
    match_files = match_files[:num_matches]
    
    freezer = MatchStateFreezer(data_dir=processed_dir)
    freeze_minutes = [20, 45, 70]
    
    raw_records = []
    too_vague_count = 0
    
    for idx, match_file in enumerate(match_files):
        logging.info(f"[{idx+1}/{len(match_files)}] Processing file {os.path.basename(match_file)}")
        
        with open(match_file, "r", encoding="utf-8") as f:
            match_data = json.load(f)
            
        match_id = match_data["match_id"]
        
        for min_t in freeze_minutes:
            logging.info(f"Freezing match {match_id} at minute {min_t}...")
            
            try:
                frozen_state = freezer.freeze(match_data, min_t)
            except ValueError as e:
                logging.error(f"Leakage check failed for match {match_id} at {min_t}: {e}")
                continue
                
            if dry_run:
                predictions = mock_agent_loop(frozen_state)
            else:
                try:
                    predictions = run_agent_loop(frozen_state, model_name=model_name)
                except Exception as e:
                    logging.error(f"LLM query failed for match {match_id} at {min_t}: {e}")
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
                "home_team": frozen_state["home_team"],
                "away_team": frozen_state["away_team"],
                "freeze_minute": min_t,
                "score_at_freeze": frozen_state["score"],
                "actual_final_score": grades.get("actual", {}).get("final_score"),
                "predictions": predictions,
                "grades": grades,
                "baseline": baseline,
                "baseline_correct": baseline_correct
            }
            raw_records.append(record)
            
    metrics = calculate_metrics(raw_records)
    
    output_data = {
        "model_name": model_name,
        "dry_run": dry_run,
        "total_records": len(raw_records),
        "too_vague_count": too_vague_count,
        "metrics": metrics,
        "raw_records": raw_records
    }
    
    output_file = "results_model_1.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    logging.info("=" * 50)
    logging.info(f"Pipeline completed. Results saved to {output_file}")
    logging.info("=" * 50)


def calculate_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    gradable = [r for r in records if r["grades"].get("is_gradable", True)]
    
    accuracy_by_minute = {
        "final_result": {},
        "next_goal": {},
        "next_clear_chance": {},
        "baseline": {}
    }
    
    for min_t in [20, 45, 70]:
        min_records = [r for r in gradable if r["freeze_minute"] == min_t]
        count = len(min_records)
        
        if count > 0:
            accuracy_by_minute["final_result"][min_t] = round(sum(r["grades"]["final_result_grade"] for r in min_records) / count, 3)
            accuracy_by_minute["next_goal"][min_t] = round(sum(r["grades"]["next_goal_grade"] for r in min_records) / count, 3)
            accuracy_by_minute["next_clear_chance"][min_t] = round(sum(r["grades"]["next_clear_chance_grade"] for r in min_records) / count, 3)
            accuracy_by_minute["baseline"][min_t] = round(sum(r["baseline_correct"] for r in min_records) / count, 3)
        else:
            accuracy_by_minute["final_result"][min_t] = 0.0
            accuracy_by_minute["next_goal"][min_t] = 0.0
            accuracy_by_minute["next_clear_chance"][min_t] = 0.0
            accuracy_by_minute["baseline"][min_t] = 0.0

    bins = [
        {"name": "0-30%", "range": (0.0, 0.3)},
        {"name": "30-70%", "range": (0.3, 0.7)},
        {"name": "70-100%", "range": (0.7, 1.01)}
    ]
    
    calibration = {}
    
    for pred_type in ["final_result", "next_goal", "next_clear_chance"]:
        calibration[pred_type] = {}
        
        for b in bins:
            bin_name = b["name"]
            low, high = b["range"]
            
            conf_key = f"{pred_type}_confidence"
            bin_records = [
                r for r in gradable 
                if low <= r["predictions"].get(conf_key, 0.0) < high
            ]
            
            bin_count = len(bin_records)
            if bin_count > 0:
                avg_confidence = sum(r["predictions"].get(conf_key, 0.0) for r in bin_records) / bin_count
                avg_accuracy = sum(r["grades"].get(f"{pred_type}_grade", 0) for r in bin_records) / bin_count
                
                calibration[pred_type][bin_name] = {
                    "count": bin_count,
                    "avg_predicted_confidence": round(avg_confidence, 3),
                    "actual_accuracy": round(avg_accuracy, 3)
                }
            else:
                calibration[pred_type][bin_name] = {
                    "count": 0,
                    "avg_predicted_confidence": 0.0,
                    "actual_accuracy": 0.0
                }
                
    return {
        "accuracy_by_minute": accuracy_by_minute,
        "calibration": calibration
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pulse In-Play Match Reasoning Pipeline v1")
    parser.add_argument("--model", type=str, default="qwen3.6-27b", help="Model Name")
    parser.add_argument("--matches", type=int, default=20, help="Number of matches")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    run_pipeline(
        model_name=args.model,
        num_matches=args.matches,
        dry_run=args.dry_run
    )
