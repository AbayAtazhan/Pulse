import os
import re
import json
import logging
import requests
from typing import Dict, Any, Union

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SYSTEM_PROMPT = """You are a professional football (soccer) analyst. You will be given the state of a live football match frozen at a specific minute.
The state includes the team names, the score at the freeze minute, and the chronological list of key events (goals, shots, cards, substitutions) up to that minute.

Your task is to analyze the current situation (momentum, tactics, match state) and make specific, calibrated predictions for the remainder of the match.

You MUST respond strictly with a valid JSON object. Do not include any explanations, introduction, markdown code block wrappers (like ```json), or trailing text. Your response must be parsed successfully by python's json.loads().

The JSON object must contain exactly the following keys:
1. "situational_read": (string) A concise, high-quality analysis of the game state up to the freeze minute. Who is dominating? What are the key tactical shifts and threats?
2. "next_goal": (string) The team that will score the next goal. Must be exactly one of: "home", "away", or "no_more_goals".
3. "next_goal_confidence": (float) Your confidence in this next_goal prediction, strictly between 0.0 and 1.0.
4. "final_result": (string) The final result of the match (taking into account the current score and remainder of the game). Must be exactly one of: "home_win", "away_win", or "draw".
5. "final_result_confidence": (float) Your confidence in this final_result prediction, strictly between 0.0 and 1.0.
6. "next_clear_chance": (string) The team that will create the next clear chance (e.g. shot on target, high xG shot). Must be exactly one of: "home" or "away".
7. "next_clear_chance_confidence": (float) Your confidence in this next_clear_chance prediction, strictly between 0.0 and 1.0.
8. "is_gradable": (boolean) Set this to true if you are providing specific, concrete predictions. Set this to false ONLY if you are unable to make specific predictions or are writing vague hedging statements (e.g. "either team can win").

Double-check that all confidence values are floats between 0.0 and 1.0, and the string values match the options above.
"""

def format_frozen_state(frozen_state: Dict[str, Any]) -> str:
    home = frozen_state.get("home_team", "Home Team")
    away = frozen_state.get("away_team", "Away Team")
    minute = frozen_state.get("freeze_minute", 0)
    
    score = frozen_state.get("score", "0-0")
    if isinstance(score, dict):
        score_str = f"{score.get('home', 0)}-{score.get('away', 0)}"
    else:
        score_str = str(score)
        
    events = frozen_state.get("events_so_far", frozen_state.get("events", []))
    
    lines = [
        f"Match: {home} vs {away}",
        f"Freeze Minute: {minute}",
        f"Score at minute {minute}: {home} {score_str} {away}",
        "",
        "Events up to this minute (chronological):"
    ]
    
    if not events:
        lines.append("  (No key events recorded yet)")
    else:
        for e in events:
            evt_min = e.get("minute", 0)
            evt_sec = e.get("second", 0)
            team = e.get("team", "Unknown")
            etype = e.get("type", "Event")
            player = e.get("player")
            details = e.get("details", "")
            
            player_str = f" - {player}" if player else ""
            detail_str = f" ({details})" if details else ""
            lines.append(f"  [{evt_min}:{evt_sec:02d}] {team} | {etype}{player_str}{detail_str}")
            
    return "\n".join(lines)


def clean_json_response(raw_text: str) -> str:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```$", "", cleaned)
    return cleaned.strip()


def validate_predictions(data: Dict[str, Any]) -> Dict[str, Any]:
    required_keys = {
        "situational_read": str,
        "next_goal": str,
        "next_goal_confidence": (int, float),
        "final_result": str,
        "final_result_confidence": (int, float),
        "next_clear_chance": str,
        "next_clear_chance_confidence": (int, float),
        "is_gradable": bool
    }
    
    for key, expected_type in required_keys.items():
        if key not in data:
            raise ValueError(f"Missing required key in response: '{key}'")
        if not isinstance(data[key], expected_type):
            raise TypeError(f"Invalid type for key '{key}': expected {expected_type}, got {type(data[key])}")
            
    valid_next_goal = ["home", "away", "no_more_goals"]
    if data["next_goal"] not in valid_next_goal:
        raise ValueError(f"Invalid next_goal value: '{data['next_goal']}'. Must be one of {valid_next_goal}")
        
    valid_final_result = ["home_win", "away_win", "draw"]
    if data["final_result"] not in valid_final_result:
        raise ValueError(f"Invalid final_result value: '{data['final_result']}'. Must be one of {valid_final_result}")
        
    valid_next_chance = ["home", "away"]
    if data["next_clear_chance"] not in valid_next_chance:
        raise ValueError(f"Invalid next_clear_chance value: '{data['next_clear_chance']}'. Must be one of {valid_next_chance}")
        
    for conf_key in ["next_goal_confidence", "final_result_confidence", "next_clear_chance_confidence"]:
        val = float(data[conf_key])
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"Confidence value '{conf_key}' must be in range [0.0, 1.0], got {val}")
        data[conf_key] = val
        
    return data


def call_llm(system_prompt: str, user_prompt: str, model_name: str, temperature: float = 0.0) -> str:
    if "gemma" in model_name.lower():
        openai_base = "http://localhost:8000/v1"
        openai_key = "dummy"
        logging.info(f"Routing Gemma query to locally forwarded port: {openai_base}")
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "content-type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": 2048,
        }
        endpoint = f"{openai_base.rstrip('/')}/chat/completions"
        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    
    if base_url:
        logging.info(f"Using Anthropic messages API via proxy: {base_url}")
        headers = {
            "Authorization": f"Bearer {token}" if token else "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model_name,
            "max_tokens": 2048,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        endpoint = f"{base_url.rstrip('/')}/v1/messages"
        
        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        
        blocks = response.json().get("content", [])
        text_content = "".join(b["text"] for b in blocks if b.get("type") == "text").strip()
        return text_content
        
    else:
        openai_base = os.environ.get("OPENAI_API_BASE", "http://localhost:8000/v1")
        openai_key = os.environ.get("OPENAI_API_KEY", "dummy")
        logging.info(f"Using OpenAI completions API via base: {openai_base}")
        
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "content-type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": 2048,
        }
        endpoint = f"{openai_base.rstrip('/')}/chat/completions"
        
        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        
        return response.json()["choices"][0]["message"]["content"].strip()


def run_agent_loop(frozen_state: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    match_id = frozen_state.get("match_id", 0)
    freeze_minute = frozen_state.get("freeze_minute", 0)
    user_prompt = format_frozen_state(frozen_state)
    
    raw_response = ""
    parsed_json = None
    error_msg = None
    
    try:
        logging.info(f"Querying model '{model_name}' for match {match_id} at minute {freeze_minute}...")
        raw_response = call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model_name=model_name,
            temperature=0.0
        )
        
        cleaned_response = clean_json_response(raw_response)
        parsed_json = json.loads(cleaned_response)
        parsed_json = validate_predictions(parsed_json)
        logging.info(f"Successfully received valid predictions for match {match_id} at minute {freeze_minute}.")
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logging.error(f"Error in agent loop for match {match_id} (minute {freeze_minute}): {error_msg}")
        parsed_json = {
            "situational_read": f"ERROR: {error_msg}",
            "next_goal": "no_more_goals",
            "next_goal_confidence": 0.0,
            "final_result": "draw",
            "final_result_confidence": 0.0,
            "next_clear_chance": "home",
            "next_clear_chance_confidence": 0.0,
            "is_gradable": False
        }
        
    finally:
        log_dir = "logs/prompts"
        os.makedirs(log_dir, exist_ok=True)
        
        safe_model_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", model_name)
        log_file = os.path.join(log_dir, f"{match_id}_{freeze_minute}_{safe_model_name}.json")
        
        log_data = {
            "frozen_state": frozen_state,
            "raw_response": raw_response,
            "parsed_json": parsed_json,
            "error": error_msg
        }
        
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(log_data, f, ensure_ascii=False, indent=4)
            logging.info(f"Saved execution log to {log_file}")
        except Exception as log_err:
            logging.error(f"Failed to save log file: {log_err}")
            
    if error_msg:
        raise RuntimeError(f"Agent loop failed for match {match_id}: {error_msg}")
        
    return parsed_json


if __name__ == "__main__":
    fake_state = {
        "match_id": 9999,
        "home_team": "Manchester City",
        "away_team": "Liverpool",
        "freeze_minute": 45,
        "score": "1-0",
        "events_so_far": [
            {"minute": 0, "second": 0, "team": "Manchester City", "type": "Half Start", "player": None, "details": ""},
            {"minute": 12, "second": 45, "team": "Manchester City", "type": "Shot", "player": "Erling Haaland", "details": "Shot outcome: Saved"},
            {"minute": 23, "second": 10, "team": "Manchester City", "type": "Goal", "player": "Erling Haaland", "details": "Shot outcome: Goal"},
            {"minute": 35, "second": 15, "team": "Liverpool", "type": "Card", "player": "Virgil van Dijk", "details": "Card type: Yellow Card"},
            {"minute": 45, "second": 0, "team": "Manchester City", "type": "Half End", "player": None, "details": ""}
        ]
    }
    
    test_model = os.environ.get("ANTHROPIC_MODEL", "qwen3.6-27b")
    try:
        result = run_agent_loop(fake_state, model_name=test_model)
        print(json.dumps(result, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"Test failed: {e}")
