import os
import json
import logging
from typing import List, Dict, Any
from statsbombpy import sb

# Настройка логирования для отслеживания процесса парсинга
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StatsBombParser:
    """
    Модуль 1: Data Ingestion (Загрузка данных)
    Отвечает за загрузку открытых данных StatsBomb и формирование 
    чистого поминутного таймлайна событий для каждого матча.
    """
    
    def __init__(self, output_dir: str = "data/processed"):
        """
        Инициализация парсера. Автоматически создает папку для сохранения очищенных данных.
        """
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def fetch_matches(self, competition_id: int, season_id: int) -> List[int]:
        """
        Получает список ID всех матчей для заданного турнира и сезона.
        Пример: Чемпионат Мира 2022 имеет competition_id=43 и season_id=106.
        """
        logging.info(f"Fetching matches for competition {competition_id}, season {season_id}...")
        matches = sb.matches(competition_id=competition_id, season_id=season_id)
        match_ids = matches['match_id'].tolist()
        logging.info(f"Found {len(match_ids)} matches.")
        return match_ids

    def extract_match_events(self, match_id: int) -> Dict[str, Any]:
        """
        Загружает события конкретного матча и очищает их от шума.
        Мы оставляем только ключевые моменты (Голы, Карточки, Удары, Замены, Старт/Конец тайма),
        которые понадобятся LLM для понимания хода игры (momentum).
        """
        logging.info(f"Extracting events for match_id: {match_id}")
        
        # Получаем датафрейм со всеми событиями матча
        events_df = sb.events(match_id=match_id)
        
        # КРИТИЧНО: Сортируем события строго в хронологическом порядке, 
        # чтобы в будущем избежать утечки данных (future leakage)
        events_df = events_df.sort_values(by=['minute', 'second', 'timestamp'])
        
        # Извлекаем названия играющих команд
        unique_teams = events_df['team_id'].unique()
        home_team = events_df[events_df['team_id'] == unique_teams[0]]['team'].iloc[0]
        away_team = events_df[events_df['team_id'] == unique_teams[1]]['team'].iloc[0]
        
        timeline = []
        
        # Проходим по всем событиям и формируем чистый таймлайн
        for _, row in events_df.iterrows():
            event_type = row['type']
            
            # Нас интересуют только события, влияющие на ход игры
            if event_type in ['Shot', 'Foul Committed', 'Bad Behaviour', 'Substitution', 'Half Start', 'Half End']:
                
                # Базовый скелет события
                event_data = {
                    "minute": int(row['minute']),
                    "second": int(row['second']),
                    "team": str(row['team']) if 'team' in row else None,
                    "player": str(row['player']) if 'player' in row and not type(row['player']) == float else None,
                    "type": str(event_type),
                    "details": ""
                }
                
                # Добавляем важные детали в зависимости от типа события
                if event_type == 'Shot':
                    outcome = row.get('shot_outcome', '')
                    event_data['details'] = f"Shot outcome: {outcome}"
                    if outcome == 'Goal':
                        event_data['type'] = 'Goal' # Явно выделяем голы из ударов
                        
                elif event_type == 'Substitution':
                    replacement = row.get('substitution_replacement', '')
                    event_data['details'] = f"Replaced by: {replacement}"
                    
                elif event_type in ['Foul Committed', 'Bad Behaviour']:
                    card = row.get('foul_committed_card', row.get('bad_behaviour_card', ''))
                    # Фильтруем обычные фолы, оставляем только те, за которые дали карточку
                    if isinstance(card, str) and card:
                        event_data['type'] = 'Card'
                        event_data['details'] = f"Card type: {card}"
                    else:
                        continue # Пропускаем фол без карточки
                
                # Добавляем отфильтрованное событие в общий таймлайн
                if event_data['type'] in ['Goal', 'Card', 'Substitution', 'Shot', 'Half Start', 'Half End']:
                    timeline.append(event_data)
                
        match_data = {
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "events": timeline
        }
        
        return match_data

    def save_match_data(self, match_data: Dict[str, Any]):
        """
        Сохраняет сформированный JSON с таймлайном матча.
        """
        match_id = match_data['match_id']
        file_path = os.path.join(self.output_dir, f"{match_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(match_data, f, ensure_ascii=False, indent=4)
        logging.info(f"Saved match {match_id} data to {file_path}")

if __name__ == "__main__":
    # Пример использования (тестируем на Чемпионате Мира 2022)
    parser = StatsBombParser(output_dir="data/processed")
    
    # Запрашиваем ID всех матчей ЧМ 2022
    match_ids = parser.fetch_matches(competition_id=43, season_id=106)
    
    # Для демонстрации обрабатываем только первый матч из списка
    if match_ids:
        test_match_id = match_ids[0]
        data = parser.extract_match_events(test_match_id)
        parser.save_match_data(data)
        logging.info("Test extraction complete. Check data/processed folder.")
