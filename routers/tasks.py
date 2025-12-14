from typing import List

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from models import Task, User
from database import get_async_session
from schemas import TaskCreate, TaskUpdate, TaskResponse
from dependencies import get_current_user
from utils import (
    calculate_urgency,
    calculate_days_until_deadline,
    determine_quadrant,
)

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.get("", response_model=List[TaskResponse])
async def get_all_tasks(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> List[TaskResponse]:
    if current_user.role.value == "admin":
        result = await db.execute(select(Task))
    else:
        result = await db.execute(select(Task).where(Task.user_id == current_user.id))

    tasks = result.scalars().all()

    tasks_with_days = []
    for task in tasks:
        days = calculate_days_until_deadline(task.deadline_at)
        status_message = None

        if days is not None:
            if days < 0:
                status_message = "Задача просрочена"
            elif days == 0:
                status_message = "Дедлайн сегодня"
            else:
                status_message = f"До дедлайна осталось {days} дн."

        task_dict = task.__dict__.copy()
        task_dict["days_until_deadline"] = days
        task_dict["status_message"] = status_message

        tasks_with_days.append(TaskResponse(**task_dict))

    return tasks_with_days


@router.get("/today", response_model=List[TaskResponse])
async def get_tasks_today(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> List[TaskResponse]:
    today = datetime.utcnow().date()

    if current_user.role.value == "admin":
        result = await db.execute(
            select(Task).where(
                Task.deadline_at.isnot(None),
                func.date(Task.deadline_at) == today,
                Task.completed == False,
            )
        )
    else:
        result = await db.execute(
            select(Task).where(
                Task.deadline_at.isnot(None),
                func.date(Task.deadline_at) == today,
                Task.completed == False,
                Task.user_id == current_user.id,
            )
        )

    tasks = result.scalars().all()

    tasks_with_days = []
    for task in tasks:
        days = calculate_days_until_deadline(task.deadline_at)
        status_message = None

        if days is not None:
            if days < 0:
                status_message = "Задача просрочена"
            elif days == 0:
                status_message = "Дедлайн сегодня"
            else:
                status_message = f"До дедлайна осталось {days} дн."

        task_dict = task.__dict__.copy()
        task_dict["days_until_deadline"] = days
        task_dict["status_message"] = status_message

        tasks_with_days.append(TaskResponse(**task_dict))

    return tasks_with_days


@router.get("/quadrant/{quadrant}", response_model=List[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> List[TaskResponse]:
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4",
        )

    if current_user.role.value == "admin":
        result = await db.execute(select(Task).where(Task.quadrant == quadrant))
    else:
        result = await db.execute(
            select(Task).where(Task.quadrant == quadrant, Task.user_id == current_user.id)
        )

    tasks = result.scalars().all()

    tasks_with_days = []
    for task in tasks:
        days = calculate_days_until_deadline(task.deadline_at)
        status_message = None

        if days is not None:
            if days < 0:
                status_message = "Задача просрочена"
            elif days == 0:
                status_message = "Дедлайн сегодня"
            else:
                status_message = f"До дедлайна осталось {days} дн."

        task_dict = task.__dict__.copy()
        task_dict["days_until_deadline"] = days
        task_dict["status_message"] = status_message

        tasks_with_days.append(TaskResponse(**task_dict))

    return tasks_with_days


@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> List[TaskResponse]:
    keyword = f"%{q.lower()}%"

    if current_user.role.value == "admin":
        result = await db.execute(
            select(Task).where((Task.title.ilike(keyword)) | (Task.description.ilike(keyword)))
        )
    else:
        result = await db.execute(
            select(Task).where(
                ((Task.title.ilike(keyword)) | (Task.description.ilike(keyword))),
                Task.user_id == current_user.id,
            )
        )

    tasks = result.scalars().all()

    if not tasks:
        raise HTTPException(
            status_code=404,
            detail="По данному запросу ничего не найдено",
        )

    tasks_with_days = []
    for task in tasks:
        days = calculate_days_until_deadline(task.deadline_at)
        status_message = None

        if days is not None:
            if days < 0:
                status_message = "Задача просрочена"
            elif days == 0:
                status_message = "Дедлайн сегодня"
            else:
                status_message = f"До дедлайна осталось {days} дн."

        task_dict = task.__dict__.copy()
        task_dict["days_until_deadline"] = days
        task_dict["status_message"] = status_message

        tasks_with_days.append(TaskResponse(**task_dict))

    return tasks_with_days


@router.get("/status/{status}", response_model=List[TaskResponse])
async def get_tasks_by_status(
    status: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> List[TaskResponse]:
    if status not in ["completed", "pending"]:
        raise HTTPException(
            status_code=404,
            detail="Недопустимый статус. Используйте: completed или pending",
        )

    is_completed = status == "completed"

    if current_user.role.value == "admin":
        result = await db.execute(select(Task).where(Task.completed == is_completed))
    else:
        result = await db.execute(
            select(Task).where(Task.completed == is_completed, Task.user_id == current_user.id)
        )

    tasks = result.scalars().all()

    tasks_with_days = []
    for task in tasks:
        days = calculate_days_until_deadline(task.deadline_at)
        status_message = None

        if days is not None:
            if days < 0:
                status_message = "Задача просрочена"
            elif days == 0:
                status_message = "Дедлайн сегодня"
            else:
                status_message = f"До дедлайна осталось {days} дн."

        task_dict = task.__dict__.copy()
        task_dict["days_until_deadline"] = days
        task_dict["status_message"] = status_message

        tasks_with_days.append(TaskResponse(**task_dict))

    return tasks_with_days


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав доступа")

    days = calculate_days_until_deadline(task.deadline_at)
    status_message = None

    if days is not None:
        if days < 0:
            status_message = "Задача просрочена"
        elif days == 0:
            status_message = "Дедлайн сегодня"
        else:
            status_message = f"До дедлайна осталось {days} дн."

    task_dict = task.__dict__.copy()
    task_dict["days_until_deadline"] = days
    task_dict["status_message"] = status_message

    return TaskResponse(**task_dict)


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    is_urgent = calculate_urgency(task.deadline_at)
    quadrant = determine_quadrant(task.is_important, is_urgent)

    new_task = Task(
        title=task.title,
        description=task.description,
        is_important=task.is_important,
        is_urgent=is_urgent,
        quadrant=quadrant,
        completed=False,
        deadline_at=task.deadline_at,
        user_id=current_user.id,
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    days = calculate_days_until_deadline(new_task.deadline_at)
    status_message = None

    if days is not None:
        if days < 0:
            status_message = "Задача просрочена"
        elif days == 0:
            status_message = "Дедлайн сегодня"
        else:
            status_message = f"До дедлайна осталось {days} дн."

    task_dict = new_task.__dict__.copy()
    task_dict["days_until_deadline"] = days
    task_dict["status_message"] = status_message

    return TaskResponse(**task_dict)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав доступа")

    update_data = task_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(task, field, value)

    is_urgent = calculate_urgency(task.deadline_at)
    task.is_urgent = is_urgent
    task.quadrant = determine_quadrant(task.is_important, is_urgent)

    await db.commit()
    await db.refresh(task)

    days = calculate_days_until_deadline(task.deadline_at)
    status_message = None

    if days is not None:
        if days < 0:
            status_message = "Задача просрочена"
        elif days == 0:
            status_message = "Дедлайн сегодня"
        else:
            status_message = f"До дедлайна осталось {days} дн."

    task_dict = task.__dict__.copy()
    task_dict["days_until_deadline"] = days
    task_dict["status_message"] = status_message

    return TaskResponse(**task_dict)


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав доступа")

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


@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав доступа")

    task.completed = True
    task.completed_at = datetime.now()

    await db.commit()
    await db.refresh(task)

    days = calculate_days_until_deadline(task.deadline_at)
    status_message = None

    if days is not None:
        if days < 0:
            status_message = "Задача просрочена"
        elif days == 0:
            status_message = "Дедлайн сегодня"
        else:
            status_message = f"До дедлайна осталось {days} дн."

    task_dict = task.__dict__.copy()
    task_dict["days_until_deadline"] = days
    task_dict["status_message"] = status_message

    return TaskResponse(**task_dict)
