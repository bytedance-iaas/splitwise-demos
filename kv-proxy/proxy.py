from dotenv import load_dotenv
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import httpx
import os

# Initialize the FastAPI app
app = FastAPI()

load_dotenv()

# Base URLs for the two vLLM processes (set to the root of the API)
PREFILL_BASE_URLS = os.getenv("PREFILL_ENDPOINTS", "http://localhost:8060").split(",")
DECODE_BASE_URLS = os.getenv("DECODE_ENDPOINTS", "http://localhost:8070").split(",")
LISTEN_PORT = os.getenv("LISTEN_PORT", 8080)
LISTEN_HOST = os.getenv("LISTEN_HOST", "0.0.0.0")

# Initialize variables to hold the persistent clients
app.state.prefill_clients = None
app.state.decode_clients = None

counter = 0


@app.on_event("startup")
async def startup_event():
    """
    Initialize persistent HTTPX clients for vLLM services on startup.
    """
    app.state.decode_clients = [
        httpx.AsyncClient(timeout=None, base_url=url) for url in DECODE_BASE_URLS
    ]
    app.state.prefill_clients = [
        httpx.AsyncClient(timeout=None, base_url=url) for url in PREFILL_BASE_URLS
    ]


@app.on_event("shutdown")
async def shutdown_event():
    """
    Close the persistent HTTPX clients on shutdown.
    """
    for prefill_client in app.state.prefill_clients:
        await prefill_client.aclose()

    for decode_client in app.state.decode_clients:
        await decode_client.aclose()


async def send_request_to_prefill(
    client: httpx.AsyncClient, url_path: str, req_data: dict
):
    """
    Args:
        client (httpx.AsyncClient): The persistent HTTPX client.
        url_path (str): The URL path to send the request to.
        req_data (dict): The JSON payload to send.
    Returns:
        Response: The response from the prefill service.
    """
    req_data = req_data.copy()
    req_data["max_tokens"] = 1
    req_data["max_completion_tokens"] = 1
    response = await client.post(url_path, json=req_data)  # Correct endpoint path
    response.raise_for_status()
    return response


async def send_request_to_decode(
    client: httpx.AsyncClient, url_path: str, req_data: dict
):
    """
    Asynchronously stream the response from a vLLM process using a persistent client.

    Args:
        client (httpx.AsyncClient): The persistent HTTPX client.
        url_path (str): The URL path to send the request to.
        req_data (dict): The JSON payload to send.

    Yields:
        bytes: Chunks of the response data.
    """
    async with client.stream(
        "POST", url_path, json=req_data
    ) as response:  # Correct endpoint path
        response.raise_for_status()
        async for chunk in response.aiter_bytes():
            yield chunk


@app.post("/v1/chat/completions")
@app.post("/v1/completions")
async def proxy_request(request: Request):
    global counter
    """
    Proxy endpoint that forwards requests to two vLLM services.

    Args:
        request (Request): The incoming HTTP request.

    Returns:
        StreamingResponse: The streamed response from the second vLLM service.
    """
    counter += 1
    req_data = await request.json()
    req_path = request.url.path
    try:
        prefill_client = app.state.prefill_clients[
            counter % len(app.state.prefill_clients)
        ]
        # Send request to prefill worker, ignore the response
        await send_request_to_prefill(prefill_client, req_path, req_data)

        decode_client = app.state.decode_clients[
            counter % len(app.state.decode_clients)
        ]

        # Stream response from decode worker
        async def generate_stream():
            async for chunk in send_request_to_decode(
                decode_client, req_path, req_data
            ):
                yield chunk

        return StreamingResponse(generate_stream(), media_type="application/json")
    except Exception as e:
        print(f"Error streaming response from vLLM: {e}")
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=LISTEN_HOST, port=LISTEN_PORT)
