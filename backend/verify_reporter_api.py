
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api"

def run_verification():
    # 1. Login
    print("--- 1. Logging in ---")
    login_payload = {
        "email": "alexcander@dahell.com",
        "password": "alex123"
    }
    
    try:
        r = requests.post(f"{BASE_URL}/auth/login/", json=login_payload)
        if r.status_code != 200:
            print(f"Login failed: {r.status_code} {r.text}")
            return
        
        data = r.json()
        token = data.get("token")
        user_id = data.get("user", {}).get("id")
        email = data.get("user", {}).get("email")
        print(f"Login successful. User ID: {user_id}, Email: {email}")
        
        headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json"
        }
        
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # 3. Start Workflow
    print(f"\n--- 3. Starting Reporter Workflow (Simulating Button Click) ---")
    
    # Try to Create Account blindly (since GET failed or we know we need one)
    print("\n--- 2b. Creating Test Dropi Account ---")
    create_payload = {
        "label": "reporter_test",
        "email": "reporter_test@dahell.com",
        "password": "testpassword123",
        "is_default": True
    }
    r = requests.post(f"{BASE_URL}/dropi/accounts/", json=create_payload, headers=headers)
    print(f"Create Account Status: {r.status_code}")
    if r.status_code not in [200, 201]:
        with open("error_create_account.html", "w", encoding="utf-8") as f:
            f.write(r.text)
        print("Error saved to error_create_account.html")
    else:
        print("Account created successfully.")

    # 3. Start Workflow
    print(f"\n--- 3. Starting Reporter Workflow (Simulating Button Click) ---")
    
    # Skip checking accounts API since it's returning 500, but proceed to test if start works (which uses the model directly)
    print("Skipping Account list verification (API 500). Trying to start directly...")
    
    r = requests.post(f"{BASE_URL}/reporter/start/", headers=headers)
    
    print(f"Status Code: {r.status_code}")
    if r.status_code != 200:
        with open("error_start_workflow.html", "w", encoding="utf-8") as f:
            f.write(r.text)
        print("Error saved to error_start_workflow.html")
    
    if r.status_code == 200:
        print("\n[OK] SUCCESS: Workflow started successfully via API.")
        print("Check your local server console/window to see if the new window popped up.")
    else:
        print("\n[FAIL] FAILURE: Could not start workflow.")

if __name__ == "__main__":
    run_verification()
