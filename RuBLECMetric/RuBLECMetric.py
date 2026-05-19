# ============================================================
# RuBLECMetric С РАСШИРЕННЫМИ ВОЗМОЖНОСТЯМИ NLTK
# ============================================================

import re
import json
import os
from collections import defaultdict
from typing import List, Dict, Tuple, Set, Optional
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# ПРОВЕРКА ЗАВИСИМОСТЕЙ
# ============================================================

LEMMATIZATION_AVAILABLE = False
STEMMER_AVAILABLE = False
POS_TAGGING_AVAILABLE = False
USE_LEMMATIZER = False  # Флаг для выбора метода

try:
    import nltk
    from nltk.tokenize import word_tokenize
    
    # Скачивание необходимых данных
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    nltk.download('averaged_perceptron_tagger_ru', quiet=True)
    nltk.download('stopwords', quiet=True)
    
    # Стеммер (легковесная альтернатива)
    from nltk.stem.snowball import SnowballStemmer
    STEMMER_AVAILABLE = True
    stemmer = SnowballStemmer("russian")
    
    # POS-теггер (части речи)
    try:
        nltk.data.find('taggers/averaged_perceptron_tagger_ru')
        POS_TAGGING_AVAILABLE = True
    except LookupError:
        pass
    
    # Основная лемматизация (rsmorphy)
    try:
        from rsmorphy_lemmatizer import RSMorphyTransformer
        LEMMATIZATION_AVAILABLE = True
        lemmatizer = RSMorphyTransformer()
        USE_LEMMATIZER = True
        print("✅ Используется rsmorphy-lemmatizer (точная лемматизация)")
    except ImportError:
        if STEMMER_AVAILABLE:
            USE_LEMMATIZER = False
            print("✅ rsmorphy-lemmatizer не найден, используется SnowballStemmer (стемминг)")
        else:
            print("⚠️ Доступна только базовая токенизация")
    
except ImportError as e:
    print(f"⚠️ NLTK не установлен: {e}")
    print("   Установите: pip install nltk")

# ============================================================
# УМНЫЕ СТОП-СЛОВА
# ============================================================

class StopWordsManager:
    """Менеджер стоп-слов с сохранением SQL операторов"""
    
    SQL_KEYWORDS_TO_KEEP = {
        'или', 'и', 'не', 'без', 'до', 'от', 'для', 'по', 'с', 'со',
        'в', 'во', 'на', 'за', 'у', 'о', 'об', 'при', 'через', 'над',
        'под', 'между', 'против', 'кроме', 'вместо', 'ради'
    }
    
    NUMBERS_TO_KEEP = {'один', 'два', 'три', 'четыре', 'пять', 'раз'}
    QUESTION_WORDS_TO_KEEP = {'кто', 'что', 'какой', 'какая', 'какое', 'какие', 
                              'где', 'когда', 'почему', 'зачем', 'сколько'}
    
    @classmethod
    def get_russian_stop_words(cls) -> Set[str]:
        try:
            from nltk.corpus import stopwords
            nltk.download('stopwords', quiet=True)
            all_stopwords = set(stopwords.words('russian'))
        except:
            all_stopwords = set()
        
        words_to_keep = cls.SQL_KEYWORDS_TO_KEEP | cls.NUMBERS_TO_KEEP | cls.QUESTION_WORDS_TO_KEEP
        filtered = all_stopwords - words_to_keep
        
        # Добавляем специфические стоп-слова
        filtered.update({
            'бы', 'же', 'ли', 'ну', 'уж', 'ведь', 'вот', 'вдруг', 'опять',
            'потом', 'теперь', 'тогда', 'там', 'тут', 'здесь', 'весь', 'вся',
            'все', 'всё', 'всего', 'всем', 'всеми', 'всех'
        })
        
        return filtered


RUSSIAN_STOP_WORDS = StopWordsManager.get_russian_stop_words()


# ============================================================
# УЛУЧШЕННАЯ ЛЕММАТИЗАЦИЯ (выбирает лучший метод)
# ============================================================

class TextProcessor:
    """Обработка текста с выбором оптимального метода"""
    
    @staticmethod
    def process(text: str, use_pos_filter: bool = False) -> List[str]:
        """
        Обрабатывает текст:
        - Токенизация через NLTK
        - Лемматизация/стемминг (автовыбор)
        - Опциональная фильтрация по частям речи
        - Удаление стоп-слов
        - СОХРАНЕНИЕ чисел (важно для WHERE, LIMIT, BETWEEN)
        """
        # Токенизация
        tokens = word_tokenize(text, language="russian")
        
        # Частеречная разметка (если нужна и доступна)
        if use_pos_filter and POS_TAGGING_AVAILABLE and USE_LEMMATIZER:
            try:
                tagged = nltk.pos_tag(tokens, lang='rus')
                important_tags = {'NOUN', 'VERB', 'ADJ', 'ADV', 'NUM'}  # NUM - числительные
                tokens = [word for word, tag in tagged if tag.split()[0] in important_tags]
            except:
                pass
        
        # Нормализация
        processed = []
        for token in tokens:
            # Пропускаем пустые токены
            if len(token) < 1:
                continue
            
            # Проверяем это буква ИЛИ это цифра (число)
            is_valid = token.isalpha() or token.isdigit()
            
            # Также сохраняем числа с десятичной точкой (например, 20.5)
            if not is_valid:
                # Проверяем, может быть это число с точкой?
                try:
                    float(token)
                    is_valid = True
                except ValueError:
                    pass
            
            if not is_valid:
                continue
            
            # Нормализация (только для букв, числа не изменяем)
            if token.isdigit() or token.replace('.', '').isdigit():
                # Числа оставляем как есть
                normalized = token
            elif USE_LEMMATIZER and LEMMATIZATION_AVAILABLE:
                try:
                    normalized = lemmatizer.transform([token])[0]
                except:
                    normalized = token.lower()
            elif STEMMER_AVAILABLE:
                normalized = stemmer.stem(token.lower())
            else:
                normalized = token.lower()
            
            # Фильтрация стоп-слов (НО не удаляем числа)
            if normalized.isdigit() or normalized.replace('.', '').isdigit():
                # Числа никогда не удаляем
                processed.append(normalized)
                continue
            
            if normalized.lower() in RUSSIAN_STOP_WORDS:
                continue
            
            processed.append(normalized.lower())
        
        return processed

# ============================================================
# ПАРСЕР SQL (улучшенный с NLTK)
# ============================================================

class SQLParser:
    """Парсер SQL с использованием NLTK для улучшенного извлечения"""
    
    SQL_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'HAVING', 'ORDER', 'LIMIT',
        'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'ON', 'AND', 'OR', 'NOT',
        'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL', 'AS', 'DISTINCT', 'COUNT',
        'SUM', 'AVG', 'MAX', 'MIN', 'ASC', 'DESC', 'EXCEPT', 'INTERSECT', 'UNION'
    }
    
    @staticmethod
    def extract_tables(sql: str) -> Set[str]:
        """Извлекает имена таблиц из SQL"""
        sql_upper = sql.upper()
        tables = set()
        
        from_match = re.search(r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\s+AS\s+[a-zA-Z_]+)?)', sql_upper, re.IGNORECASE)
        if from_match:
            table = from_match.group(1).split()[0]
            tables.add(table.lower())
        
        join_matches = re.finditer(r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\s+AS\s+[a-zA-Z_]+)?)', sql_upper, re.IGNORECASE)
        for match in join_matches:
            table = match.group(1).split()[0]
            tables.add(table.lower())
        
        comma_match = re.search(r'FROM\s+([^WHEREGROUPORDERLIMIT]+)', sql_upper, re.IGNORECASE)
        if comma_match:
            from_clause = comma_match.group(1)
            for table in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)', from_clause):
                table_name = table.group(1).lower()
                if table_name not in SQLParser.SQL_KEYWORDS and len(table_name) > 1:
                    tables.add(table_name)
        
        return tables
    
    @staticmethod
    def extract_values(sql: str) -> Set[str]:
        """
        Извлекает значения из SQL (числа и строки).
        Использует NLTK для улучшенного извлечения.
        """
        values = set()
        
        # Числа
        numbers = re.findall(r'\b\d+\b', sql)
        values.update(numbers)
        
        # Строки в кавычках
        strings = re.findall(r"'([^']*)'", sql)
        strings.extend(re.findall(r'"([^"]*)"', sql))
        values.update([s.lower() for s in strings if len(s) > 1])
        
        return values
    
    @staticmethod
    def extract_operators(sql: str) -> Dict[str, List]:
        """Извлекает операторы сравнения"""
        operators = defaultdict(list)
        
        patterns = [
            (r'(\w+)\s*(>=|<=|!=|<>|=|>|<)\s*(\d+)', 3),
            (r'(\w+)\s*(>=|<=|!=|<>|=|>|<)\s*\'([^\']+)\'', 3),
            (r'BETWEEN\s+(\d+)\s+AND\s+(\d+)', 2),
            (r'IN\s*\(([^)]+)\)', 1),
            (r'LIKE\s+\'([^\']+)\'', 1),
        ]
        
        for pattern, group_count in patterns:
            matches = re.finditer(pattern, sql, re.IGNORECASE)
            for match in matches:
                if group_count == 3:
                    col, op, val = match.groups()
                    operators[op.lower()].append({'column': col.lower(), 'value': val})
                elif group_count == 2:
                    v1, v2 = match.groups()
                    operators['between'].append({'min': v1, 'max': v2})
                elif group_count == 1:
                    if 'LIKE' in pattern:
                        operators['like'].append(match.group(1))
                    elif 'IN' in pattern:
                        operators['in'].append([v.strip() for v in match.group(1).split(',')])
        
        return dict(operators)
    
    @staticmethod
    def extract_aggregations(sql: str) -> List[str]:
        """Извлекает агрегатные функции"""
        aggs = []
        agg_funcs = ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']
        
        for func in agg_funcs:
            if re.search(rf'\b{func}\s*\(', sql, re.IGNORECASE):
                aggs.append(func.lower())
        
        return aggs
    
    @staticmethod
    def extract_limit(sql: str) -> Optional[int]:
        """Извлекает LIMIT"""
        match = re.search(r'LIMIT\s+(\d+)', sql, re.IGNORECASE)
        return int(match.group(1)) if match else None
    
    @staticmethod
    def extract_order(sql: str) -> Optional[str]:
        """Извлекает ORDER BY"""
        if re.search(r'ORDER BY.*\bASC\b', sql, re.IGNORECASE):
            return 'asc'
        elif re.search(r'ORDER BY.*\bDESC\b', sql, re.IGNORECASE):
            return 'desc'
        return None


# ============================================================
# ЗАГРУЗЧИК КОНФИГУРАЦИИ
# ============================================================

class ConfigLoader:
    """Загрузчик конфигурационных JSON файлов"""
    
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self._cache = {}
    
    def _load_json(self, filename: str) -> Dict:
        if filename in self._cache:
            return self._cache[filename]
        
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._cache[filename] = data
                return data
        except FileNotFoundError:
            return {}
    
    def get_tables(self) -> Dict[str, str]:
        data = self._load_json('tables.json')
        return data.get('tables', {})
    
    def get_operators(self) -> Dict[str, Dict]:
        data = self._load_json('operators.json')
        return data.get('operators', {})
    
    def get_aggregations(self) -> Dict[str, Dict]:
        data = self._load_json('aggregations.json')
        return data.get('aggregations', {})
    
    def get_hallucinations(self) -> Dict[str, Dict]:
        data = self._load_json('hallucinations.json')
        return data.get('hallucinations', {})
    
    def get_opposites(self) -> Dict[str, List[str]]:
        data = self._load_json('opposites.json')
        return data.get('opposites', {})
    
    def get_weights(self) -> Dict[str, float]:
        data = self._load_json('weights.json')
        return data.get('weights', {})
    
    def get_sql_to_russian(self) -> Dict[str, List[str]]:
        result = {}
        
        for op, config in self.get_operators().items():
            result[op] = config.get('synonyms', [])
        
        for agg, config in self.get_aggregations().items():
            result[agg] = config.get('synonyms', [])
        
        result['limit_1'] = ['самый', 'единственный', 'первый', 'последний', 
                            'наименьш', 'наибольш', 'наименьшим', 'наибольшим']
        
        return result


# ============================================================
# ОСНОВНОЙ КЛАСС RuBLECMetric
# ============================================================

class RuBLECMetric:
    """
    RuBLECMetric с использованием возможностей NLTK:
    - Автовыбор между лемматизацией и стеммингом
    - Опциональная фильтрация по частям речи
    - Умные стоп-слова (сохраняют SQL операторы)
    """
    
    def __init__(self, config_dir: str = "config", use_pos_filter: bool = False):
        """
        Аргументы:
            config_dir: путь к папке с JSON конфигами
            use_pos_filter: фильтровать ли слова по частям речи (только с лемматизацией)
        """
        self.use_pos_filter = use_pos_filter and POS_TAGGING_AVAILABLE and USE_LEMMATIZER
        
        self.sql_parser = SQLParser()
        self.parse_cache = {}
        
        # Загрузка конфигурации
        self.config_loader = ConfigLoader(config_dir)
        
        # Загрузка словарей
        self.table_translations = self.config_loader.get_tables()
        self.operator_configs = self.config_loader.get_operators()
        self.aggregation_configs = self.config_loader.get_aggregations()
        self.hallucination_map = {
            table: info.get('forbidden_words', [])
            for table, info in self.config_loader.get_hallucinations().items()
        }
        self.opposites = self.config_loader.get_opposites()
        self.weights = self.config_loader.get_weights()
        
        if not self.weights:
            self.weights = {
                'tables': 0.30,
                'operators': 0.25,
                'aggregations': 0.15,
                'order': 0.10,
                'limit': 0.05,
                'hallucination': 0.15,
            }
        
        # Основной словарь SQL → русские синонимы
        self.sql_to_russian = self.config_loader.get_sql_to_russian()
        
        # Построение обратного словаря
        self._build_reverse_dict()
        
        # Информация о состоянии
        self._print_status()
    
    def _print_status(self):
        """Выводит информацию о состоянии метрики"""
        print("=" * 50)
        print("RuBLECMetric инициализирована")
        print("=" * 50)
        if USE_LEMMATIZER and LEMMATIZATION_AVAILABLE:
            print("✅ Лемматизация: rsmorphy-lemmatizer (точная)")
        elif STEMMER_AVAILABLE:
            print("⚠️ Лемматизация: SnowballStemmer (стемминг, менее точный)")
        else:
            print("⚠️ Лемматизация: отсутствует (буквальное сравнение)")
        
        if self.use_pos_filter:
            print("✅ Фильтрация по частям речи: включена")
        else:
            print("📝 Фильтрация по частям речи: выключена")
        
        print(f"📚 Стоп-слов: {len(RUSSIAN_STOP_WORDS)} (SQL операторы сохранены)")
        print("=" * 50)
    
    def _build_reverse_dict(self):
        """Строит обратный словарь для быстрого поиска"""
        self.russian_to_operator = {}
        for op, synonyms in self.sql_to_russian.items():
            for syn in synonyms:
                base_syn = syn[:-2] if len(syn) > 3 and syn[-2:] in ['ая', 'ый', 'ое', 'ий'] else syn
                self.russian_to_operator[base_syn] = op
                self.russian_to_operator[syn] = op
    
    def _process_text(self, text: str) -> List[str]:
        """Обработка текста через TextProcessor"""
        return TextProcessor.process(text, use_pos_filter=self.use_pos_filter)
    
    def _get_operator_weight(self, op_type: str) -> float:
        return self.operator_configs.get(op_type, {}).get('weight', 1.0)
    
    def _parse_sql_cached(self, sql: str) -> Dict:
        if sql in self.parse_cache:
            return self.parse_cache[sql]
        
        result = {
            'tables': self.sql_parser.extract_tables(sql),
            'values': self.sql_parser.extract_values(sql),
            'operators': self.sql_parser.extract_operators(sql),
            'aggregations': self.sql_parser.extract_aggregations(sql),
            'limit': self.sql_parser.extract_limit(sql),
            'order': self.sql_parser.extract_order(sql),
        }
        
        if len(self.parse_cache) > 500:
            self.parse_cache.pop(next(iter(self.parse_cache)))
        self.parse_cache[sql] = result
        
        return result
    
    def _check_table_match(self, sql_tables: Set[str], text_lemmas: List[str]) -> Tuple[float, List[str]]:
        if not sql_tables:
            return 1.0, []
        
        matched = 0
        missing = []
        text_str = ' '.join(text_lemmas)
        
        for table in sql_tables:
            table_lower = table.lower()
            found = False
            
            if table_lower in self.hallucination_map:
                for bad_word in self.hallucination_map[table_lower]:
                    if bad_word in text_str:
                        missing.append(f"hallucination_{table}→{bad_word}")
                        found = True
                        break
            
            if not found:
                for lemma in text_lemmas:
                    if table_lower in lemma or lemma in table_lower:
                        found = True
                        break
                
                if not found and table_lower in self.table_translations:
                    translation = self.table_translations[table_lower]
                    for lemma in text_lemmas:
                        if translation in lemma or lemma in translation:
                            found = True
                            break
                
                if found:
                    matched += 1
                else:
                    missing.append(table)
        
        base_score = matched / len(sql_tables) if sql_tables else 1.0
        return base_score, missing
    
    def _check_operators_match(self, sql_operators: Dict, text: str, text_lemmas: List[str]) -> Tuple[float, List[str]]:
        if not sql_operators:
            return 1.0, []
        
        matched_weight = 0
        total_weight = 0
        errors = []
        text_lower = text.lower()
        
        for op_type in sql_operators.keys():
            weight = self._get_operator_weight(op_type)
            total_weight += weight
            
            found = False
            synonyms = self.sql_to_russian.get(op_type, [op_type])
            
            for syn in synonyms:
                if any(syn in lemma for lemma in text_lemmas):
                    found = True
                    break
                if syn in text_lower:
                    found = True
                    break
            
            if found:
                matched_weight += weight
            else:
                errors.append(f"missing_{op_type}")
                
                if op_type in self.opposites:
                    for opp in self.opposites[op_type]:
                        if opp in text_lower or any(opp in lemma for lemma in text_lemmas):
                            matched_weight -= weight * 0.5
                            errors.append(f"opposite_{op_type}")
                            break
        
        score = matched_weight / total_weight if total_weight > 0 else 1.0
        return max(0.0, min(1.0, score)), errors
    
    def _check_aggregations_match(self, sql_aggs: List[str], text_lemmas: List[str]) -> Tuple[float, List[str]]:
        if not sql_aggs:
            return 1.0, []
        
        matched = 0
        errors = []
        
        for agg in sql_aggs:
            synonyms = self.sql_to_russian.get(agg, [agg])
            found = False
            
            for syn in synonyms:
                if any(syn in lemma for lemma in text_lemmas):
                    matched += 1
                    found = True
                    break
            
            if not found:
                errors.append(f"missing_{agg}")
                
                if agg in self.opposites:
                    for opp in self.opposites[agg]:
                        if any(opp in lemma for lemma in text_lemmas):
                            matched -= 0.5
                            errors.append(f"opposite_{agg}")
                            break
        
        score = matched / len(sql_aggs) if sql_aggs else 1.0
        return max(0.0, min(1.0, score)), errors
    
    def _check_order_match(self, sql_order: Optional[str], text_lemmas: List[str]) -> Tuple[float, List[str]]:
        if not sql_order:
            return 1.0, []
        
        synonyms = self.sql_to_russian.get(sql_order, [sql_order])
        found = any(syn in lemma for lemma in text_lemmas for syn in synonyms)
        
        if not found and sql_order in self.opposites:
            for opp in self.opposites[sql_order]:
                if any(opp in lemma for lemma in text_lemmas):
                    return 0.3, [f"opposite_{sql_order}"]
        
        return (1.0 if found else 0.0), ([] if found else [f"missing_{sql_order}"])
    
    def _check_limit_match(self, sql_limit: Optional[int], text: str, text_lemmas: List[str]) -> Tuple[float, List[str]]:
        if sql_limit is None:
            return 1.0, []
        
        limit_num = str(sql_limit)
        found = limit_num in text
        
        if sql_limit == 1 and not found:
            limit_phrases = self.sql_to_russian.get('limit_1', [])
            found = any(phrase in text.lower() for phrase in limit_phrases)
            
            if not found:
                for lemma in text_lemmas:
                    if lemma in ['наименьш', 'наибольш', 'минимальн', 'максимальн']:
                        if 'возраст' not in text.lower():
                            found = True
                            break
        
        return (1.0 if found else 0.0), ([] if found else [f"missing_limit_{limit_num}"])
    
    def _check_hallucinations(self, sql_tables: Set[str], text: str, text_lemmas: List[str]) -> Tuple[float, List[str]]:
        if not sql_tables:
            return 1.0, []
        
        text_lower = text.lower()
        text_str = ' '.join(text_lemmas)
        hallucinations = []
        
        for table in sql_tables:
            table_lower = table.lower()
            
            if table_lower in self.hallucination_map:
                for bad_word in self.hallucination_map[table_lower]:
                    if bad_word in text_lower or bad_word in text_str:
                        hallucinations.append(f"hallucination_{table}→'{bad_word}'")
                        break
        
        if hallucinations:
            return 0.0, hallucinations
        return 1.0, []
    
    def calculate_blec(self, sql: str, text: str) -> Dict:
        """Вычисляет BLEC оценку"""
        
        sql_components = self._parse_sql_cached(sql)
        text_lemmas = self._process_text(text)
        
        table_score, table_errors = self._check_table_match(
            sql_components['tables'], text_lemmas
        )
        operator_score, operator_errors = self._check_operators_match(
            sql_components['operators'], text, text_lemmas
        )
        agg_score, agg_errors = self._check_aggregations_match(
            sql_components['aggregations'], text_lemmas
        )
        order_score, order_errors = self._check_order_match(
            sql_components['order'], text_lemmas
        )
        limit_score, limit_errors = self._check_limit_match(
            sql_components['limit'], text, text_lemmas
        )
        hallucination_score, hallucination_errors = self._check_hallucinations(
            sql_components['tables'], text, text_lemmas
        )
        
        all_errors = (table_errors + operator_errors + agg_errors + 
                      order_errors + limit_errors + hallucination_errors)
        
        component_scores = {
            'tables': table_score,
            'operators': operator_score,
            'aggregations': agg_score,
            'order': order_score,
            'limit': limit_score,
            'hallucination': hallucination_score,
        }
        
        total_score = sum(self.weights.get(comp, 0.1) * score 
                          for comp, score in component_scores.items())
        
        critical_penalty = len([e for e in all_errors if 'opposite' in e or 'hallucination' in e]) * 0.1
        total_score = max(0.0, min(1.0, total_score - critical_penalty))
        
        return {
            'score': round(total_score, 3),
            'components': component_scores,
            'errors': all_errors,
            'hallucinations_detected': [e for e in all_errors if 'hallucination' in e],
            'details': {
                'tables_found': list(sql_components['tables']),
                'operators_found': list(sql_components['operators'].keys()),
                'aggregations_found': sql_components['aggregations'],
                'values_found': list(sql_components['values'])[:5],
                'limit': sql_components['limit'],
                'order': sql_components['order'],
                'text_lemmas': text_lemmas[:10],
            }
        }
    
    def evaluate_batch(self, pairs: List[Tuple[str, str]]) -> List[Dict]:
        return [self.calculate_blec(sql, text) for sql, text in pairs]
    
    def clear_cache(self):
        self.parse_cache.clear()


# ============================================================
# БЫСТРЫЙ ТЕСТ
# ============================================================

def quick_test():
    """Быстрый тест метрики"""
    
    try:
        blec = RuBLECMetric(config_dir="config", use_pos_filter=False)
    except FileNotFoundError as e:
        print(f"❌ Ошибка: {e}")
        return
    
    test_cases = [
        ("SELECT name FROM student WHERE age > 20", 
         "показать имена студентов старше 20 лет"),
        ("SELECT name FROM student WHERE age > 20 OR country = 'USA'", 
         "показать студентов старше 20 лет или из США"),
        ("SELECT name FROM student WHERE country = 'USA' AND age < 25", 
         "найти студентов из США и младше 25 лет"),
        ("SELECT max(age) FROM Dogs", 
         "какой максимальный возраст собак"),
        ("SELECT avg(age) FROM Dogs", 
         "каков средний возраст собак"),
    ]
    
    print("\n" + "=" * 60)
    print("БЫСТРЫЙ ТЕСТ")
    print("=" * 60)
    
    for sql, text in test_cases:
        result = blec.calculate_blec(sql, text)
        status = "✅" if result['score'] > 0.5 else "⚠️"
        print(f"\nSQL: {sql}")
        print(f"Текст: {text}")
        print(f"Score: {result['score']:.3f} {status}")
        if result['errors']:
            print(f"  Ошибки: {', '.join(result['errors'][:2])}")


if __name__ == "__main__":
    quick_test()