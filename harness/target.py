import os

import requests
from dotenv import load_dotenv

load_dotenv()

URL = os.environ["STRIDE_URL"].rstrip("/")
HEADERS = {"Authorization": f"Bearer {os.environ['STRIDE_API_TOKEN']}"}


def wake_up():
    # the free Render plan sleeps when idle, so the first call can take a minute
    requests.get(f"{URL}/health", timeout=120).raise_for_status()


def ask(question, source="harness"):
    response = requests.post(
        f"{URL}/chat",
        json={"question": question, "source": source},
        headers=HEADERS,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["answer"], data["sources"]
