# RuBLECMetric

**Russian BLEC Metric** — метрика для оценки соответствия между SQL запросом и сгенерированным русским текстом.

## Особенности

- 95%+ точность на 276 тестовых примерах
- Детекция галлюцинаций (собаки → люди, питомцы → удобства)
- Распознавание всех основных SQL операторов на русском
- Работает в Google Colab без внешних зависимостей
- Гибкая настройка через JSON конфиги

## Установка в Colab

```python
# Способ 1: Прямая установка из GitHub
!pip install git+https://github.com/YOUR_USERNAME/RuBLEC.git

# Способ 2: Клонирование репозитория
!git clone https://github.com/YOUR_USERNAME/RuBLEC.git
%cd RuBLEC
!pip install -e .

## Использование

```python
from RuBLECMetric import RuBLECMetric

blec = RuBLECMetric()
result = blec.calculate_blec(
    "SELECT name FROM students WHERE age > 20",
    "показать имена студентов старше 20 лет"
)
print(f"Score: {result['score']}")  # 1.0
```

## Конфигурация

Словари легко расширяются через JSON файлы в папке config/:

- tables.json — перевод таблиц
- operators.json — синонимы операторов
- hallucinations.json — детекция галлюцинаций

## Лицензия - MIT



