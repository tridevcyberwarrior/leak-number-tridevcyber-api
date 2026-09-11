from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import duckdb
import os

app = FastAPI()

# Lazy connection for serverless
_db_conn = None

def get_db():
    global _db_conn
    if _db_conn is None:
        _db_conn = duckdb.connect()
        _db_conn.execute("INSTALL httpfs;")
        _db_conn.execute("LOAD httpfs;")
    return _db_conn

# ... HTML same rakho ...

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={
                "status": "rejected",
                "message": "Invalid endpoint. Use /api/FetchData?Number=XXXXXXXXXX",
                "Developer": "@tridevcyber"
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "Developer": "@tridevcyber"}
    )

@app.get("/", response_class=HTMLResponse)
def root_landing_page():
    return HTMLResponse(content=LANDING_PAGE_HTML, status_code=200)

@app.get("/api/FetchData")  # /api/ prefix add kiya
def fetch_data(Number: str = Query(None)):
    # Validation
    if not Number or not Number.isdigit() or len(Number) != 10:
        return JSONResponse(
            status_code=400,
            content={
                "status": "rejected",
                "message": "Invalid. Use /api/FetchData?Number=10digits",
                "Developer": "@tridevcyber"
            }
        )
    
    last_digit = Number[-1]
    
    primary_url = f"https://huggingface.co/datasets/CutehackX/hitek-data-bucket/resolve/main/final_master_shard_{last_digit}.parquet"
    alt_url = f"https://huggingface.co/datasets/CutehackX/hitek-data-bucket/resolve/main/alt_master_shard_{last_digit}.parquet"
    
    try:
        con = get_db()
        
        # Parameterized query - SQL Injection safe
        query = """
            SELECT * FROM read_parquet(?) WHERE mobile = ?
            UNION ALL
            SELECT * FROM read_parquet(?) WHERE alt = ?
        """
        
        df = con.execute(query, [primary_url, Number, alt_url, Number]).df()
        
        # Split results
        main_recs = df[df['mobile'] == Number].to_dict('records') if 'mobile' in df.columns else []
        alt_recs = df[df['alt'] == Number].to_dict('records') if 'alt' in df.columns else []
        
        if not main_recs and not alt_recs:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "not_found", 
                    "phone": Number,
                    "Developer": "@tridevcyber"
                }
            )
            
        return {
            "status": "success", 
            "phone": Number,
            "main_count": len(main_recs),
            "alt_count": len(alt_recs),
            "data": {
                "main": main_recs,
                "alt": alt_recs
            },
            "Developer": "@tridevcyber"
        }
        
    except duckdb.Error as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "db_error",
                "message": str(e),
                "Developer": "@tridevcyber"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Internal server error",
                "Developer": "@tridevcyber"
            }
        )

# Vercel handler
handler = app
