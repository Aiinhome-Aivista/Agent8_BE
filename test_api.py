import requests

# Login to get token
resp = requests.post("http://localhost:8001/api/auth/login", json={
    "email": "soniakhatun9786@gmail.com",
    "password": "123456"
})

if resp.status_code == 200:
    token = resp.json()["token"]
    print("Login successful")
    
    # Get policies
    pol_resp = requests.get("http://localhost:8001/api/policies", headers={
        "Authorization": f"Bearer {token}"
    })
    print("Policies API Status:", pol_resp.status_code)
    print("Policies Response:", pol_resp.json())
else:
    print("Login failed:", resp.status_code, resp.text)
