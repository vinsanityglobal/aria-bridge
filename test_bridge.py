import requests

def test_health():
    url = "http://localhost:8001/health"
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    print(f"Body: {response.text}")

if __name__ == "__main__":
    test_health()
