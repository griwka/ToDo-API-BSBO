from typing import List

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from sqlalchemy import Date

from models import Task
from database import get_async_session
from schemas import TaskCreate, TaskUpdate, TaskResponse
from utils import (
    calculate_urgency,
    calculate_days_until_deadline,
    determine_quadrant,
)

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


# GET ALL TASKS - Получить все задачи
@router.get("", response_model=List[TaskResponse])
async def get_all_tasks(
    db: AsyncSession = Depends(get_async_session),
) -> List[TaskResponse]:
    result = await db.execute(select(Task))  # SELECT * FROM tasks
    tasks = result.scalars().all()
    return tasks

@router.get("/today", response_model=list[TaskResponse])
async def get_tasks_today(
    db: AsyncSession = Depends(get_async_session),
):
    today = datetime.utcnow().date()

    result = await db.execute(
        select(Task).where(
            Task.deadline_at.isnot(None),
            Task.deadline_at.cast(Date) == today,
            Task.completed == False
        )
    )

    tasks = result.scalars().all()

    
    return tasks

# GET TASKS BY QUADRANT - Получить задачи по квадранту
@router.get("/quadrant/{quadrant}", response_model=List[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    db: AsyncSession = Depends(get_async_session),
) -> List[TaskResponse]:
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4",
        )

    result = await db.execute(
        select(Task).where(Task.quadrant == quadrant)
    )  # SELECT * FROM tasks WHERE quadrant = ...
    tasks = result.scalars().all()
    return tasks


# SEARCH TASKS - Поиск задач
@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_session),
) -> List[TaskResponse]:
    keyword = f"%{q.lower()}%"  # %keyword% для LIKE

    result = await db.execute(
        select(Task).where(
            (Task.title.ilike(keyword)) | (Task.description.ilike(keyword))
        )
    )
    tasks = result.scalars().all()

    if not tasks:
        raise HTTPException(
            status_code=404,
            detail="По данному запросу ничего не найдено",
        )

    return tasks


# GET TASKS BY STATUS - Получить задачи по статусу
@router.get("/status/{status}", response_model=List[TaskResponse])
async def get_tasks_by_status(
    status: str,
    db: AsyncSession = Depends(get_async_session),
) -> List[TaskResponse]:
    if status not in ["completed", "pending"]:
        raise HTTPException(
            status_code=404,
            detail="Недопустимый статус. Используйте: completed или pending",
        )

    is_completed = status == "completed"

    result = await db.execute(
        select(Task).where(Task.completed == is_completed)
    )  # SELECT * FROM tasks WHERE completed = True/False
    tasks = result.scalars().all()
    return tasks


# GET TASK BY ID - Получить задачу по ID (с расчётом срока до дедлайна)
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> TaskResponse:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )  # SELECT * FROM tasks WHERE id = ...
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Расчёт дней до дедлайна и статусного сообщения
    days = calculate_days_until_deadline(task.deadline_at)
    status_message = None

    if days is not None:
        if days < 0:
            status_message = "Задача просрочена"
        elif days == 0:
            status_message = "Дедлайн сегодня"
        else:
            status_message = f"До дедлайна осталось {days} дн."

    # Добавляем временные атрибуты к ORM-объекту, чтобы их подхватил TaskResponse
    task.days_until_deadline = days
    task.status_message = status_message

    return task


# POST - СОЗДАНИЕ НОВОЙ ЗАДАЧИ (с дедлайном и автосчётом срочности)
@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_async_session),
) -> TaskResponse:
    # Вычисляем срочность на основе дедлайна
    is_urgent = calculate_urgency(task.deadline_at)
    # Определяем квадрант на основе важности и срочности
    quadrant = determine_quadrant(task.is_important, is_urgent)

    new_task = Task(
        title=task.title,
        description=task.description,
        is_important=task.is_important,
        is_urgent=is_urgent,
        quadrant=quadrant,
        completed=False,
        deadline_at=task.deadline_at,
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    # Для ответа тоже можно посчитать дни/статус
    days = calculate_days_until_deadline(new_task.deadline_at)
    status_message = None
    if days is not None:
        if days < 0:
            status_message = "Задача просрочена"
        elif days == 0:
            status_message = "Дедлайн сегодня"
        else:
            status_message = f"До дедлайна осталось {days} дн."

    new_task.days_until_deadline = days
    new_task.status_message = status_message

    return new_task


# PUT - ОБНОВЛЕНИЕ ЗАДАЧИ (учитываем изменения дедлайна/важности)
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_async_session),
) -> TaskResponse:
    # ШАГ 1: ищем задачу по ID
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # ШАГ 2: берём только реально переданные поля
    update_data = task_update.model_dump(exclude_unset=True)

    # ШАГ 3: обновляем атрибуты ORM-объекта
    for field, value in update_data.items():
        setattr(task, field, value)

    # ШАГ 4: пересчитываем срочность и квадрант, если изменились дедлайн/важность
    # даже если не изменились явно — всё равно считаем от актуальных значений
    is_urgent = calculate_urgency(task.deadline_at)
    task.is_urgent = is_urgent
    task.quadrant = determine_quadrant(task.is_important, is_urgent)

    await db.commit()
    await db.refresh(task)

    # Расчёт дней и статуса для ответа
    days = calculate_days_until_deadline(task.deadline_at)
    status_message = None
    if days is not None:
        if days < 0:
            status_message = "Задача просрочена"
        elif days == 0:
            status_message = "Дедлайн сегодня"
        else:
            status_message = f"До дедлайна осталось {days} дн."

    task.days_until_deadline = days
    task.status_message = status_message

    return task


# DELETE - УДАЛЕНИЕ ЗАДАЧИ
@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    deleted_task_info = {
        "id": task.id,
        "title": task.title,
    }

    await db.delete(task)
    await db.commit()

    return {
        "message": "Задача успешно удалена",
        "id": deleted_task_info["id"],
        "title": deleted_task_info["title"],
    }


# PATCH - ОТМЕТИТЬ ЗАДАЧУ ВЫПОЛНЕННОЙ
@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> TaskResponse:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    task.completed = True
    task.completed_at = datetime.now()

    await db.commit()
    await db.refresh(task)

    # Для завершённой задачи тоже посчитаем дни/статус относительно дедлайна
    days = calculate_days_until_deadline(task.deadline_at)
    status_message = None
    if days is not None:
        if days < 0:
            status_message = "Задача просрочена"
        elif days == 0:
            status_message = "Дедлайн сегодня"
        else:
            status_message = f"До дедлайна осталось {days} дн."

    task.days_until_deadline = days
    task.status_message = status_message

    return task
