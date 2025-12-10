from fastapi import APIRouter, HTTPException, status, Response
from datetime import datetime

from schemas import TaskCreate, TaskUpdate, TaskResponse
from database import tasks_db


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
    responses={404: {"description": "Task not found"}},
)




@router.get("/")
async def get_all_tasks() -> dict:
    return {
        "count": len(tasks_db),
        "tasks": tasks_db,
    }


@router.get("/quadrant/{quadrant}")
async def get_tasks_by_quadrant(quadrant: str) -> dict:
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4",
        )

    filtered_tasks = [
        task
        for task in tasks_db
        if task["quadrant"] == quadrant
    ]

    return {
        "quadrant": quadrant,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks,
    }




@router.get("/status/{status}")
async def get_tasks_by_status(status: str) -> dict:
    if status not in ["completed", "pending"]:
        raise HTTPException(
            status_code=404,
            detail="Неверный статус. Используйте: completed или pending",
        )

    need_completed = status == "completed"

    filtered = [
        task for task in tasks_db
        if task["completed"] == need_completed
    ]

    return {
        "status": status,
        "count": len(filtered),
        "tasks": filtered,
    }


@router.get("/search")
async def search_tasks(q: str) -> dict:
    if len(q) < 2:
        raise HTTPException(
            status_code=400,
            detail="Поисковый запрос должен быть минимум 2 символа",
        )

    query = q.lower()

    filtered = [
        task for task in tasks_db
        if query in task["title"].lower()
        or (
            task["description"] is not None
            and query in task["description"].lower()
        )
    ]

    if not filtered:
        raise HTTPException(
            status_code=404,
            detail="Задачи по данному запросу не найдены",
        )

    return {
        "query": q,
        "count": len(filtered),
        "tasks": filtered,
    }


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(task_id: int) -> TaskResponse:
    task = next(
        (task for task in tasks_db if task["id"] == task_id),
        None
    )

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    return task


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate) -> TaskResponse:
    if task.is_important and task.is_urgent:
        quadrant = "Q1"
    elif task.is_important and not task.is_urgent:
        quadrant = "Q2"
    elif not task.is_important and task.is_urgent:
        quadrant = "Q3"
    else:
        quadrant = "Q4"

    new_id = max([t["id"] for t in tasks_db], default=0) + 1

    new_task = {
        "id": new_id,
        "title": task.title,
        "description": task.description,
        "is_important": task.is_important,
        "is_urgent": task.is_urgent,
        "quadrant": quadrant,
        "completed": False,
        "created_at": datetime.now(),
    }

    tasks_db.append(new_task)
    return new_task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task_update: TaskUpdate) -> TaskResponse:
    task = next(
        (task for task in tasks_db if task["id"] == task_id),
        None
    )

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    update_data = task_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        task[field] = value

    if "is_important" in update_data or "is_urgent" in update_data:
        if task["is_important"] and task["is_urgent"]:
            task["quadrant"] = "Q1"
        elif task["is_important"] and not task["is_urgent"]:
            task["quadrant"] = "Q2"
        elif not task["is_important"] and task["is_urgent"]:
            task["quadrant"] = "Q3"
        else:
            task["quadrant"] = "Q4"

    return task


@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: int) -> TaskResponse:
    task = next(
        (task for task in tasks_db if task["id"] == task_id),
        None
    )

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    task["completed"] = True
    task["completed_at"] = datetime.now()

    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int):
    task = next(
        (task for task in tasks_db if task["id"] == task_id),
        None
    )

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    tasks_db.remove(task)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
