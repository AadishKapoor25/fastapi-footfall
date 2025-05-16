from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from typing import List
import pyodbc
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(docs_url="/docs", openapi_url="/openapi.json")

# Database configuration from .env
db_config = {
    'server': os.getenv('DB_SERVER'),
    'database': os.getenv('DB_DATABASE'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT'),
    'driver': os.getenv('DB_DRIVER')
}
valid_api_key = os.getenv('API_KEY')


# Pydantic model with validation
class Footfall(BaseModel):
    state: str = Field(..., min_length=1, max_length=100)
    district: str = Field(..., min_length=1, max_length=100)


def get_db_connection():
    try:
        conn_str = (
            f"DRIVER={{{db_config['driver']}}};"
            f"SERVER={db_config['server']};"
            f"PORT={db_config['port']};"
            f"DATABASE={db_config['database']};"
            f"UID={db_config['user']};"
            f"PWD={db_config['password']}"
        )
        connection = pyodbc.connect(conn_str)
        return connection
    except pyodbc.Error as e:
        print(f"Error connecting to SQL Server: {str(e)}")
        return None


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Footfall Data API. Use /footfall/ to get or post data."}


@app.get("/footfall/", response_model=List[Footfall])
async def get_footfall_data():
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT TOP 10 state, district FROM footfall_data_Api")
        columns = [column[0] for column in cursor.description]
        footfall_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return footfall_data
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if connection:
            cursor.close()
            connection.close()


@app.post("/footfall/", response_model=Footfall)
async def insert_footfall_data(footfall: Footfall, x_api_key: str = Header(...)):
    print("POST /footfall/ endpoint called")
    if x_api_key != valid_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    try:
        cursor = connection.cursor()
        insert_query = "INSERT INTO footfall_data_Api (state, district) VALUES (?, ?)"
        cursor.execute(insert_query, (footfall.state, footfall.district))
        connection.commit()
        return footfall
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if connection:
            cursor.close()
            connection.close()