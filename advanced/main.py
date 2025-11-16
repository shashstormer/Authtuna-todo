# main.py
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from bson import ObjectId

# --- App-specific Imports ---
from database import TodoCollection  # Our MongoDB collection

# --- AuthTuna Imports ---
from authtuna import init_app
# This is the main service facade
from authtuna.integrations import auth_service
# These are our security dependencies
from authtuna.integrations import get_current_user, RoleChecker
# AuthTuna's User model and the DeletedUser model for our cleanup task
from authtuna.core.database import User, DeletedUser, db_manager
from sqlalchemy import select, update


# --- Pydantic Models for our MongoDB Todos ---
# We need a helper class to handle MongoDB's '_id'
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, *args, **kwargs):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema, *args, **kwargs):
        field_schema.update(type="string")


class Todo(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    content: str
    user_id: str  # This ID comes from authtuna's User model
    org_id: str  # This ID comes from authtuna's Organization model

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class TodoCreate(BaseModel):
    content: str
    org_id: str  # User must specify which org to create the todo in


# --- FastAPI App Setup ---
@asynccontextmanager
async def lifespan(_: FastAPI):
    await auth_service.roles.add_permission_to_role("User", "org:create", "system")
    yield
app = FastAPI(title="Advanced Todo Backend", lifespan=lifespan)

# 1. Add CORS Middleware
# This is CRITICAL for your Next.js app (on localhost:3000)
# to communicate with this backend (on localhost:8000).
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost(:[0-9]+)?", # I got apps running on multiple initial ports, so just allow all localhost ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Initialize AuthTuna
# This adds the session middleware and all API endpoints
# for /auth/login, /auth/signup, /admin, etc.
init_app(app)


# --- API Endpoints for Todos ---

@app.get("/api/todos", response_model=List[Todo])
async def get_all_todos_for_user(user: User = Depends(get_current_user)):
    """
    Get all Todos for the current user.
    This demonstrates the "advanced" logic:
    1. Get the current user from AuthTuna.
    2. Get all organizations this user belongs to from AuthTuna.
    3. Get all Todos from MongoDB that belong to any of those organizations.
    """
    # 1. Get orgs from authtuna's db
    user_orgs = await auth_service.orgs.get_user_orgs(user.id)
    org_ids = [org.id for org in user_orgs]

    if not org_ids:
        return []

    # 2. Query MongoDB for todos in those orgs
    todo_cursor = TodoCollection.find({"org_id": {"$in": org_ids}})
    todos = await todo_cursor.to_list(100)
    return todos


@app.post("/api/todos", response_model=Todo, status_code=status.HTTP_201_CREATED)
async def create_todo(todo: TodoCreate, user: User = Depends(get_current_user)):
    """
    Create a new Todo in a specific organization.
    We must verify the user is actually a member of that org first.
    """
    # 1. Verify user is in the org they claim
    user_orgs = await auth_service.orgs.get_user_orgs(user.id)
    if todo.org_id not in [org.id for org in user_orgs]:
        raise HTTPException(status_code=403, detail="You are not a member of this organization")

    # 2. Create the Todo document in MongoDB
    todo_doc = {
        "content": todo.content,
        "org_id": todo.org_id,
        "user_id": user.id  # Link to the AuthTuna user
    }
    result = await TodoCollection.insert_one(todo_doc)

    # 3. Retrieve the created document to return it
    created_todo = await TodoCollection.find_one({"_id": result.inserted_id})
    return created_todo


@app.delete("/api/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: str, user: User = Depends(get_current_user)):
    """
    Deletes a Todo.
    Crucially, it checks that the todo exists AND belongs to the user
    (or an org they are in) before deleting.
    """
    if not ObjectId.is_valid(todo_id):
        raise HTTPException(status_code=404, detail="Invalid Todo ID")

    # Find the todo in MongoDB
    todo = await TodoCollection.find_one({"_id": ObjectId(todo_id)})
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    # Security check: Get user's orgs from AuthTuna
    user_orgs = await auth_service.orgs.get_user_orgs(user.id)
    org_ids = [org.id for org in user_orgs]

    # Verify the todo is in an org the user has access to
    # (A stricter check would be todo["user_id"] == user.id)
    if todo["org_id"] not in org_ids:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this todo")

    await TodoCollection.delete_one({"_id": ObjectId(todo_id)})
    return


# --- Advanced: User Deletion Cleanup Task ---

@app.post("/api/admin/run-cleanup-step",
          dependencies=[Depends(RoleChecker("Admin"))])  #
async def run_cleanup_step():
    """
    This is the advanced user deletion task you requested.
    It finds users in authtuna's 'DeletedUser' table with cleanup_counter=0,
    deletes their data from our MongoDB, and increments the counter.
    """
    users_processed = []
    async with db_manager.get_db() as db:
        # 1. Find users in authtuna's DB marked for deletion
        #
        stmt = select(DeletedUser).where(DeletedUser.cleanup_counter == 0)
        result = await db.execute(stmt)
        users_to_cleanup = result.scalars().all()

        if not users_to_cleanup:
            return {"message": "No users found needing cleanup."}

        for user in users_to_cleanup:
            # 2. Delete their application data from MongoDB
            delete_result = await TodoCollection.delete_many(
                {"user_id": user.user_id}
            )

            # 3. Increment the cleanup_counter in authtuna's DB
            # This marks our app's data as "cleaned"
            user.cleanup_counter += 1
            db.add(user)

            users_processed.append({
                "user_id": user.user_id,
                "todos_deleted": delete_result.deleted_count
            })

        # Commit the counter increments
        await db.commit()

    return {
        "message": f"Cleanup step processed {len(users_processed)} users.",
        "details": users_processed
    }


if __name__ == "__main__":
    print("Starting AuthTuna ADVANCED Backend...")
    print("FastAPI running on http://localhost:5080")
    print("AuthTuna API at http://localhost:5080/auth")
    print("AuthTuna Admin UI at http://localhost:5080/admin/dashboard (Login with .env credentials)")
    print("Next.js UI expected on http://localhost:*")
    uvicorn.run(app, host="0.0.0.0", port=5080)
