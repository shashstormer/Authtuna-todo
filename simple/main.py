import os
os.putenv("ENV_FILE_NAME", ".env")
import uvicorn
# --- AuthTuna Imports ---
# init_app sets up all middleware and auth routers
from authtuna import init_app
# db_manager gives us access to the database session
# Base is the declarative base our Todo model must inherit from
# User is the model we will link our Todo model to
from authtuna.core.database import db_manager, Base, User
from authtuna.integrations import get_current_user_optional
# get_current_user is the dependency that protects our routes
from authtuna.integrations.fastapi_integration import get_current_user
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Column, Integer, String, ForeignKey, select
from sqlalchemy.orm import relationship, Mapped


# 1. Define our custom Todo model
# We inherit from authtuna's 'Base' so it's managed by the same system
class Todo(Base):
    __tablename__ = "todos"
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    content: Mapped[str] = Column(String, index=True)

    # This is the crucial link to the User model
    user_id: Mapped[str] = Column(String(64), ForeignKey("users.id"))

    # This relationship lets us access todo.user
    user: Mapped["User"] = relationship("User")


# 2. Setup FastAPI and Jinja2
app = FastAPI(title="Simple Todo App")
templates = Jinja2Templates(directory="templates")

# 3. Initialize AuthTuna
# This is the magic. It adds all auth routes (/auth/login, /auth/signup)
# and the session middleware.
init_app(app)


# 4. Create our App's Routes

@app.get("/")
async def root(logged_in=Depends(get_current_user_optional)):
    """
    Root page. If the user is logged in, redirect to /todos.
    If not, redirect to the authtuna login page.
    """
    # We can't use get_current_user here since it requires login.
    # We check the session cookie directly.
    if logged_in:
        return RedirectResponse(url="/todos", status_code=302)
    return RedirectResponse(url="/auth/login?return_url=/", status_code=302)


@app.get("/todos")
async def get_todos(request: Request, user: User = Depends(get_current_user_optional)):
    """
    Protected route. Only logged-in users can access this.
    It fetches *only* the todos for the current user.

    """
    if not user:
        return RedirectResponse("/")
    todos = []
    async with db_manager.get_db() as db:
        stmt = select(Todo).where(Todo.user_id == user.id)
        result = await db.execute(stmt)
        todos = result.scalars().all()

    return templates.TemplateResponse("todos.html", {
        "request": request,
        "todos": todos,
        "username": user.username
    })


@app.post("/todos/add")
async def add_todo(content: str = Form(...), user: User = Depends(get_current_user)):
    """
    Protected route to add a new todo.
    """
    async with db_manager.get_db() as db:
        new_todo = Todo(content=content, user_id=user.id)
        db.add(new_todo)
        await db.commit()

    return RedirectResponse(url="/todos", status_code=303)


@app.get("/todos/{todo_id}/delete")
async def delete_todo(todo_id: int, user: User = Depends(get_current_user)):
    """
    Protected route to delete a todo.
    Ensures a user can only delete their own todos.
    """
    async with db_manager.get_db() as db:
        stmt = select(Todo).where(Todo.id == todo_id, Todo.user_id == user.id)
        result = await db.execute(stmt)
        todo_to_delete = result.scalar_one_or_none()

        if todo_to_delete:
            await db.delete(todo_to_delete)
            await db.commit()

    return RedirectResponse(url="/todos", status_code=303)


# Add a run block for easy execution
if __name__ == "__main__":
    print("Starting AuthTuna Simple TODO App...")
    print("Access http://localhost:5080")
    # print("Sign up at http://localhost:5080/auth/signup")
    print("Login/Create account at http://localhost:5080/auth/login?return_url=/") # Just use this link as it will redirect you back after successful login after creating account.
    uvicorn.run(app, host="localhost", port=5080)
