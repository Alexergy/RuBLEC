import json
import os
from typing import Dict, List, Any

class ConfigLoader:
    """Загрузчик конфигурационных файлов для RuBLECMetric"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self._cache = {}
    
    def _load_json(self, filename: str) -> Dict:
        """Загружает JSON файл с кэшированием"""
        if filename in self._cache:
            return self._cache[filename]
        
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._cache[filename] = data
                return data
        except FileNotFoundError:
            print(f"⚠️ Файл {filepath} не найден, использую значения по умолчанию")
            return {}
    
    def get_tables(self) -> Dict[str, str]:
        """Возвращает словарь таблиц"""
        data = self._load_json('tables.json')
        return data.get('tables', {})
    
    def get_operators(self) -> Dict[str, Dict]:
        """Возвращает словарь операторов"""
        data = self._load_json('operators.json')
        return data.get('operators', {})
    
    def get_aggregations(self) -> Dict[str, Dict]:
        """Возвращает словарь агрегаций"""
        data = self._load_json('aggregations.json')
        return data.get('aggregations', {})
    
    def get_hallucinations(self) -> Dict[str, Dict]:
        """Возвращает словарь галлюцинаций"""
        data = self._load_json('hallucinations.json')
        return data.get('hallucinations', {})
    
    def get_opposites(self) -> Dict[str, List[str]]:
        """Возвращает словарь противоположностей"""
        data = self._load_json('opposites.json')
        return data.get('opposites', {})
    
    def get_weights(self) -> Dict[str, float]:
        """Возвращает веса компонентов"""
        data = self._load_json('weights.json')
        return data.get('weights', {})
    
    def get_sql_to_russian(self) -> Dict[str, List[str]]:
        """Формирует полный словарь SQL→русские слова"""
        result = {}
        
        # Добавляем операторы
        for op, config in self.get_operators().items():
            result[op] = config.get('synonyms', [])
        
        # Добавляем агрегации
        for agg, config in self.get_aggregations().items():
            result[agg] = config.get('synonyms', [])
        
        # Добавляем специальные фразы для LIMIT 1
        result['limit_1'] = ['самый', 'единственный', 'первый', 'последний', 
                            'наименьш', 'наибольш', 'наименьшим', 'наибольшим']
        
        return result
    
    def get_operator_weight(self, op: str) -> float:
        """Возвращает вес оператора"""
        operators = self.get_operators()
        return operators.get(op, {}).get('weight', 1.0)
    
    def get_aggregation_weight(self, agg: str) -> float:
        """Возвращает вес агрегации"""
        aggregations = self.get_aggregations()
        return aggregations.get(agg, {}).get('weight', 1.0)
    
    def get_hallucination_penalty(self, table: str) -> float:
        """Возвращает штраф за галлюцинацию для таблицы"""
        hallucinations = self.get_hallucinations()
        return hallucinations.get(table, {}).get('penalty', 0.5)
    
    def get_forbidden_words(self, table: str) -> List[str]:
        """Возвращает запрещённые слова для таблицы"""
        hallucinations = self.get_hallucinations()
        return hallucinations.get(table, {}).get('forbidden_words', [])
    
    def reload(self):
        """Перезагружает все конфигурации"""
        self._cache.clear()