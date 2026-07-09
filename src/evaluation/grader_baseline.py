import json
import logging
from typing import Dict, Any, List, Union

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOO_VAGUE_TO_GRADE_COUNT = 0

def get_too_vague_count() -> int:
    return TOO_VAGUE_TO_GRADE_COUNT

def reset_too_vague_count():
    global TOO_VAGUE_TO_GRADE_COUNT
    TOO_VAGUE_TO_GRADE_COUNT = 0

def grade_predictions(
    predictions: Dict[str, Any],
    real_continuation: List[Dict[str, Any]],
    home_team: str = None,
    away_team: str = None,
    frozen_score: Union[str, Dict[str, int]] = None
) -> Dict[str, Any]:
    global TOO_VAGUE_TO_GRADE_COUNT
    
    if not predictions.get("is_gradable", True):
        TOO_VAGUE_TO_GRADE_COUNT += 1
        logging.info("Prediction is flagged as too vague to grade. Incrementing counter.")
        return {
            "is_gradable": False,
            "next_goal_grade": 0,
            "final_result_grade": 0,
            "next_clear_chance_grade": 0,
            "details": "Model predictions were too vague to grade."
        }
        
    if not home_team or not away_team:
        frozen_state = predictions.get("frozen_state", {})
        home_team = home_team or frozen_state.get("home_team")
        away_team = away_team or frozen_state.get("away_team")
        frozen_score = frozen_score or frozen_state.get("score")
        
    if not home_team or not away_team:
        raise ValueError("Missing home_team or away_team.")
        
    predicted_next_goal = predictions.get("next_goal")
    actual_next_goal = "no_more_goals"
    
    for event in real_continuation:
        if event.get("type") == "Goal":
            event_team = event.get("team")
            if event_team == home_team:
                actual_next_goal = "home"
                break
            elif event_team == away_team:
                actual_next_goal = "away"
                break
                
    next_goal_grade = 1 if predicted_next_goal == actual_next_goal else 0
    
    predicted_final_result = predictions.get("final_result")
    
    home_frozen_goals = 0
    away_frozen_goals = 0
    if frozen_score:
        if isinstance(frozen_score, dict):
            home_frozen_goals = frozen_score.get("home", 0)
            away_frozen_goals = frozen_score.get("away", 0)
        elif isinstance(frozen_score, str):
            try:
                parts = frozen_score.split("-")
                home_frozen_goals = int(parts[0])
                away_frozen_goals = int(parts[1])
            except Exception:
                pass

    home_continuation_goals = sum(
        1 for e in real_continuation 
        if e.get("type") == "Goal" and e.get("team") == home_team
    )
    away_continuation_goals = sum(
        1 for e in real_continuation 
        if e.get("type") == "Goal" and e.get("team") == away_team
    )
    
    final_home_goals = home_frozen_goals + home_continuation_goals
    final_away_goals = away_frozen_goals + away_continuation_goals
    
    if final_home_goals > final_away_goals:
        actual_final_result = "home_win"
    elif final_home_goals < final_away_goals:
        actual_final_result = "away_win"
    else:
        actual_final_result = "draw"
        
    final_result_grade = 1 if predicted_final_result == actual_final_result else 0
    
    predicted_next_chance = predictions.get("next_clear_chance")
    actual_next_chance = None
    
    for event in real_continuation:
        if event.get("type") in ["Shot", "Goal"]:
            event_team = event.get("team")
            if event_team == home_team:
                actual_next_chance = "home"
                break
            elif event_team == away_team:
                actual_next_chance = "away"
                break
                
    next_clear_chance_grade = 1 if predicted_next_chance == actual_next_chance else 0
    
    return {
        "is_gradable": True,
        "next_goal_grade": next_goal_grade,
        "final_result_grade": final_result_grade,
        "next_clear_chance_grade": next_clear_chance_grade,
        "actual": {
            "next_goal": actual_next_goal,
            "final_result": actual_final_result,
            "next_clear_chance": actual_next_chance,
            "final_score": f"{final_home_goals}-{final_away_goals}"
        }
    }


def calculate_naive_baseline(frozen_state: Dict[str, Any]) -> Dict[str, Any]:
    score = frozen_state.get("score", {"home": 0, "away": 0})
    
    home_score = 0
    away_score = 0
    if isinstance(score, dict):
        home_score = score.get("home", 0)
        away_score = score.get("away", 0)
    elif isinstance(score, str):
        try:
            parts = score.split("-")
            home_score = int(parts[0])
            away_score = int(parts[1])
        except Exception:
            pass
            
    if home_score > away_score:
        predicted_result = "home_win"
    elif home_score < away_score:
        predicted_result = "away_win"
    else:
        predicted_result = "draw"
        
    return {
        "final_result": predicted_result,
        "next_goal": "no_more_goals" if home_score == away_score else ("home" if home_score > away_score else "away")
    }


if __name__ == "__main__":
    test_predictions = {
        "is_gradable": True,
        "next_goal": "home",
        "final_result": "home_win",
        "next_clear_chance": "home"
    }
    
    test_continuation = [
        {"minute": 50, "second": 10, "team": "Manchester City", "type": "Shot", "player": "Kevin De Bruyne", "details": "Shot outcome: Blocked"},
        {"minute": 65, "second": 30, "team": "Manchester City", "type": "Goal", "player": "Erling Haaland", "details": "Shot outcome: Goal"},
        {"minute": 80, "second": 0, "team": "Liverpool", "type": "Goal", "player": "Mohamed Salah", "details": "Shot outcome: Goal"}
    ]
    
    results = grade_predictions(
        predictions=test_predictions,
        real_continuation=test_continuation,
        home_team="Manchester City",
        away_team="Liverpool",
        frozen_score="1-0"
    )
    print(json.dumps(results, indent=4, ensure_ascii=False))
