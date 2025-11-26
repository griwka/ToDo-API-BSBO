# ToDo лист API

## Описание
Учебный API-проект на FastAPI с использованием матрицы Эйзенхауэра для управления задачами.

## Технологии
- Python 3.10+
- FastAPI

## Как запустить проект
```bash
git clone <ссылка на репозиторий>
cd ToDo-API-BSBO
python -m venv venv
source venv/Scripts/activate   # Windows
pip install -r requirements.txt
uvicorn main:app --reload