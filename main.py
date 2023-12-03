from fastapi import FastAPI, Form, HTTPException, Request, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import model
from db import engine,SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


# these 3 things are here for token generation
SECRET_KEY = "a6663213869b0e4cbf1e7d677297c5adf797342b4c18c3d1a59876103e9eda0b"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30



# templates are here to rendering html files
templates = Jinja2Templates(directory="templates")
# create database tables
model.Base.metadata.create_all(bind=engine)

def get_db():
    try:
        db = SessionLocal(bind=engine)
        yield db
    finally:
        db.close()







class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str or None = None


class User(BaseModel):
    username: str
    email: str or None = None
    full_name: str or None = None
    disabled: bool or None = None


class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth_2_scheme = OAuth2PasswordBearer(tokenUrl="token")


app = FastAPI()


def verify_password(plain_password, hash_password):
    return pwd_context.verify(plain_password, hash_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    if username in db:
        user_data = db[username]
        return User(**user_data)


def get_user_by_username(db, username: str):
    return db.query(model.User).filter(model.User.username == username).first()

def authenticate_user(db, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_acess_token(data: dict, expires_delta: timedelta or None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"sub": data["sub"], "exp": expire})
    encode_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encode_jwt


async def get_current_user(token: str = Depends(oauth_2_scheme), db: Session = Depends(get_db)):

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(username=username)
    except JWTError as e:
        return None

    user = get_user_by_username(db, username=token_data.username)
    if user is None:
        return None

    return user





async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user





@app.post("/token", response_model=Token)
async def login_for_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password",
                            headers={"www-Authenticate": "Bearer"})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_acess_token(data={"sub": user.username}, expires_delta=access_token_expires)
    redirect_url = f"/afterlogin?token={access_token}"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@app.get("/users/me", response_model=User)
async def read_user_me(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return current_user


@app.get("/users/me/items")
async def read_user_items(current_user: User = Depends(get_current_active_user)):
    return [{"item_id": 1, "owner": current_user}]









class Student(BaseModel):
    name:str = Field(min_length=1)
    department:str = Field(min_length=1)
    roll_number:int

STUDENTS=[]

@app.get("/afterlogin", response_class=HTMLResponse)
def read_api(request: Request, db: Session = Depends(get_db)):
    students = db.query(model.Students).all()
    return templates.TemplateResponse("index.html", {"request": request, "students": students})



# @app.get("/afterlogin", response_class=HTMLResponse, dependencies=[Depends(get_current_active_user)])
# def read_api(request: Request, db: Session = Depends(get_db)):
#     students = db.query(model.Students).all()
#     return templates.TemplateResponse("index.html", {"request": request, "students": students})







@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/", response_model=Token)
async def register(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Check if the username is already taken
    existing_user = get_user_by_username(db, form_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Create a new User instance
    user_data = {
        "username": form_data.username,
        "hashed_password": get_password_hash(form_data.password),
    }
    new_user = model.User(**user_data)
    db.add(new_user)
    db.commit()

    # Generate access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_acess_token(data={"sub": new_user.username}, expires_delta=access_token_expires)

    # Redirect to a route that requires authentication, e.g., /users/me
    redirect_url = f"/login?token={access_token}"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)








@app.post("/afterlogin")
async def create_api(
    request: Request,
    name: str = Form(...),
    department: str = Form(...),
    roll_number: int = Form(...),
    db: Session = Depends(get_db)
):
    model_student = model.Students(name=name, department=department, roll_number=roll_number)
    db.add(model_student)
    db.commit()
    return RedirectResponse(url="/afterlogin", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/edit")
async def edit_student(
    request: Request,
    student_id: int = Form(...),
    name: str = Form(...),
    department: str = Form(...),
    roll_number: int = Form(...),
    db: Session = Depends(get_db),
):
    # Fetch the student from the database
    student_to_edit = db.query(model.Students).filter(model.Students.id == student_id).first()

    if not student_to_edit:
        raise HTTPException(status_code=404, detail="Student not found")

    # Update the student details
    student_to_edit.name = name
    student_to_edit.department = department
    student_to_edit.roll_number = roll_number

    db.commit()
    return RedirectResponse(url="/afterlogin", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/delete")
async def delete_student(student_id: int = Form(...), db: Session = Depends(get_db)):
    # Fetch the student from the database
    student_to_delete = db.query(model.Students).filter(model.Students.id == student_id).first()

    if not student_to_delete:
        raise HTTPException(status_code=404, detail="Student not found")

    # Delete the student
    db.delete(student_to_delete)
    db.commit()

    return RedirectResponse(url="/afterlogin", status_code=status.HTTP_303_SEE_OTHER)

