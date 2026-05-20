from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.auth import router as auth_router 
from app.routers.profile import router as profile_router 
from app.routers.activation import router as activation_router
from app.routers.ws import router as web_socket
from app.routers.admin_vms import router as admin_vms_router
from app.routers.user_vms import router as user_vms_router



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_socket)
app.include_router(activation_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(admin_vms_router)
app.include_router(user_vms_router)


@app.get("/")
def health():
    return {
        "status" : "ok"
    }
