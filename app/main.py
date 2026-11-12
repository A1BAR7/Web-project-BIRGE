from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import lost, skills, confessions, food
from app.services.lost_images import UPLOAD_DIR

app = FastAPI(title='BIRGE Campus Community API',version='1.1.0',description='REST API for Lost & Found, Däm, SkillQos, and Ishimде')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
app.include_router(lost.router)
app.include_router(skills.router)
app.include_router(confessions.router)
app.include_router(food.router)

@app.get('/')
def home():
    return {'app':'BIRGE API','docs':'/docs','status':'running'}

FRONTEND = Path(__file__).resolve().parent.parent / 'frontend'
ASSETS = FRONTEND.parent / 'static'
ASSETS.mkdir(exist_ok=True)
app.mount('/uploads/lost_items', StaticFiles(directory=UPLOAD_DIR), name='lost-images')
app.mount('/static/images', StaticFiles(directory=ASSETS / 'images'), name='images')
app.mount('/static/fonts', StaticFiles(directory=ASSETS / 'fonts'), name='fonts')
app.mount('/static', StaticFiles(directory=FRONTEND), name='static')

app.mount('/app', StaticFiles(directory=FRONTEND, html=True), name='frontend')
