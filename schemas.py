from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# Базовая схема для Task.
# Все поля, которые есть в нашей "базе данных" tasks_db
class TaskBase(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Название задачи"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Описание задачи"
    )
    is_important: bool = Field(
        ...,
        description="Важность задачи"
    )
    is_urgent: bool = Field(
        ...,
        description="Срочность задачи"
    )


# Схема для создания новой задачи (используется в POST)
class TaskCreate(TaskBase):
    pass


# Схема для обновления задачи (используется в PUT)
# Все поля опциональные
class TaskUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        description="Новое название задачи"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Новое описание"
    )
    is_important: Optional[bool] = Field(
        None,
        description="Новая важность"
    )
    is_urgent: Optional[bool] = Field(
        None,
        description="Новая срочность"
    )
    completed: Optional[bool] = Field(
        None,
        description="Статус выполнения"
    )


# Модель для ответа (TaskResponse)
class TaskResponse(TaskBase):
    id: int = Field(
        ...,
        description="Уникальный идентификатор задачи",
        examples=[1]
    )
    quadrant: str = Field(
        ...,
        description="Квадрант матрицы Эйзенхауэра (Q1, Q2, Q3, Q4)",
        examples=["Q1"]
    )
    completed: bool = Field(
        default=False,
        description="Статус выполнения задачи"
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания задачи"
    )

    class Config:
        # понадобится позже при работе с БД
        from_attributes = True
