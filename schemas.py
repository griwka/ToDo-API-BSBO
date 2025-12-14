from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from pydantic import ConfigDict


# Базовая схема задачи (общие поля)
class TaskBase(BaseModel):
    title: str = Field(
        ...,
        description="Название задачи"
    )
    description: Optional[str] = Field(
        None,
        description="Описание задачи"
    )
    is_important: bool = Field(
        ...,
        description="Флаг важности задачи"
    )
    
    deadline_at: Optional[datetime] = Field(
        None,
        description="Плановый дедлайн задачи (дата и время)"
    )


# Схема для создания задачи
class TaskCreate(TaskBase):
    # is_urgent больше не передаём с фронта — он будет считаться автоматически
    pass


# Схема для обновления задачи
class TaskUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        description="Название задачи"
    )
    description: Optional[str] = Field(
        None,
        description="Описание задачи"
    )
    is_important: Optional[bool] = Field(
        None,
        description="Флаг важности задачи"
    )
    deadline_at: Optional[datetime] = Field(
        None,
        description="Плановый дедлайн задачи (дата и время)"
    )


# Схема для ответа (то, что уходит клиенту)
class TaskResponse(TaskBase):
    id: int = Field(
        ...,
        description="Идентификатор задачи"
    )
    is_urgent: bool = Field(
        ...,
        description="Признак срочности задачи"
    )
    quadrant: str = Field(
        ...,
        description="Квадрант матрицы Эйзенхауэра (Q1–Q4)"
    )
    completed: bool = Field(
        ...,
        description="Статус выполнения задачи"
    )
    created_at: datetime = Field(
        ...,
        description="Дата создания задачи"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Дата завершения задачи"
    )

    
    days_until_deadline: Optional[int] = Field(
        None,
        description="Количество полных дней до дедлайна"
    )
    status_message: Optional[str] = Field(
        None,
        description="Текстовый статус задачи относительно дедлайна"
    )

    # Для работы с ORM-объектами (SQLAlchemy)
    model_config = ConfigDict(from_attributes=True)



class TimingStatsResponse(BaseModel):
    completed_on_time: int = Field(
        ...,
        description="Количество задач, завершенных в срок"
    )
    completed_late: int = Field(
        ...,
        description="Количество задач, завершенных с нарушением сроков"
    )
    on_plan_pending: int = Field(
        ...,
        description="Количество задач в работе, выполняемых в соответствии с планом"
    )
    overtime_pending: int = Field(
        ...,
        description="Количество просроченных незавершенных задач"
    )
