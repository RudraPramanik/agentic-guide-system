from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/")
def list_users():
    return {"message": "Listing users from the Users Module"}

@router.post("/")
def create_user():
    return {"message": "User created in the Users Module"}