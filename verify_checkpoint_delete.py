import requests
import os
import shutil

# Configuration
BASE_URL = "http://localhost:7861/api/training"
CHECKPOINT_NAME = "TEST_CHECKPOINT_DELETE_ME"
CHECKPOINT_PATH = f"FAIRS/resources/checkpoints/{CHECKPOINT_NAME}"

def create_dummy_checkpoint():
    if not os.path.exists(CHECKPOINT_PATH):
        os.makedirs(CHECKPOINT_PATH)
        with open(os.path.join(CHECKPOINT_PATH, "dummy.keras"), "w") as f:
            f.write("dummy content")
    print(f"Created dummy checkpoint at {CHECKPOINT_PATH}")

def verify_delete():
    create_dummy_checkpoint()
    
    # Check if exists via API
    response = requests.get(f"{BASE_URL}/checkpoints")
    checkpoints = response.json()
    if CHECKPOINT_NAME not in checkpoints:
        print("Error: Checkpoint not found in API list after creation")
        return

    print("Deleting checkpoint via API...")
    response = requests.delete(f"{BASE_URL}/checkpoints/{CHECKPOINT_NAME}")
    
    if response.status_code == 200:
        print("Success: API returned 200")
    else:
        print(f"Error: API returned {response.status_code} - {response.text}")
        return

    # Verify physical deletion
    if not os.path.exists(CHECKPOINT_PATH):
        print("Success: Checkpoint folder physically deleted")
    else:
        print("Error: Checkpoint folder still exists")

if __name__ == "__main__":
    try:
        verify_delete()
    except Exception as e:
        print(f"Verification failed: {e}")
