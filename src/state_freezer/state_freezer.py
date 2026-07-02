import os
import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class MatchStateFreezer:
    """
    Модуль 2: Freeze Step (Заморозка состояния)
    Восстанавливает состояние матча (счёт + события) строго на момент
    выбранной минуты T, не допуская утечки данных из будущего (future leakage).
    """

    def __init__(self, data_dir: str = "data/processed"):
        self.data_dir = data_dir

    def load_match(self, match_id: int) -> Dict[str, Any]:
        """
        Загружает сохранённый чистый таймлайн матча (результат Модуля 1).
        """
        file_path = os.path.join(self.data_dir, f"{match_id}.json")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def freeze(self, match_data: Dict[str, Any], freeze_minute: int) -> Dict[str, Any]:
        """
        Строит "замороженное" состояние матча на минуту freeze_minute:
        - события строго до и включая freeze_minute (всё, что после T, отбрасывается)
        - счёт, посчитанный по голам внутри этого окна

        Это единственная точка, где решается, что модель "видит" — всё,
        что попадёт в результат, не должно содержать событий из будущего.
        """
        home_team = match_data["home_team"]
        away_team = match_data["away_team"]

        events_so_far = [
            event for event in match_data["events"]
            if event["minute"] <= freeze_minute
        ]

        # Защитная проверка: если сюда просочилось событие из будущего — это баг,
        # который должен ронять пайплайн, а не тихо портить результаты грейдинга.
        leaked = [e for e in events_so_far if e["minute"] > freeze_minute]
        if leaked:
            raise ValueError(
                f"Future leakage detected in match {match_data.get('match_id')}: "
                f"{len(leaked)} event(s) after freeze minute {freeze_minute}"
            )

        home_score = sum(
            1 for e in events_so_far
            if e["type"] == "Goal" and e["team"] == home_team
        )
        away_score = sum(
            1 for e in events_so_far
            if e["type"] == "Goal" and e["team"] == away_team
        )

        return {
            "match_id": match_data.get("match_id"),
            "home_team": home_team,
            "away_team": away_team,
            "freeze_minute": freeze_minute,
            "score": {"home": home_score, "away": away_score},
            "events": events_so_far,
        }

    def format_state_text(self, frozen_state: Dict[str, Any]) -> str:
        """
        Превращает замороженное состояние в текст, который можно отдать модели
        в промпте (человекочитаемый вид "score so far" + хронология событий).
        """
        home = frozen_state["home_team"]
        away = frozen_state["away_team"]
        score = frozen_state["score"]
        minute = frozen_state["freeze_minute"]

        lines = [
            f"Match frozen at minute {minute}.",
            f"Score: {home} {score['home']} - {score['away']} {away}",
            "",
            "Events so far:",
        ]

        if not frozen_state["events"]:
            lines.append("(no events yet)")
        else:
            for e in frozen_state["events"]:
                detail = f" ({e['details']})" if e.get("details") else ""
                player = f" - {e['player']}" if e.get("player") else ""
                lines.append(
                    f"  [{e['minute']}:{e['second']:02d}] {e['team']} - {e['type']}{player}{detail}"
                )

        return "\n".join(lines)


if __name__ == "__main__":
    import sys
    import io

    # Windows-консоль по умолчанию не в UTF-8, а в именах игроков встречаются
    # не-ASCII символы (é и т.п.) — перенаправляем stdout в UTF-8, чтобы демо
    # не падало на печати.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    freezer = MatchStateFreezer(data_dir="data/processed")

    # Демонстрация на уже собранном тестовом матче (Canada vs Morocco, ЧМ 2022)
    match_data = freezer.load_match(3857276)

    for minute in (20, 45, 70):
        state = freezer.freeze(match_data, freeze_minute=minute)
        logging.info(
            f"Freeze @ {minute}': score {state['score']['home']}-{state['score']['away']}, "
            f"{len(state['events'])} events visible"
        )
        print(freezer.format_state_text(state))
        print("-" * 60)
