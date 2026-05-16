import json
import os

print("--- STARTING MANUAL WRITE TEST ---")

# The fake data we want to save
dummy_data = ["Test_Car_999", "Test_Car_888"]

try:
    # Attempt to write the file
    with open("seen_cars.json", 'w') as f:
        json.dump(dummy_data, f)
    
    print("SUCCESS: Python successfully created and wrote to seen_cars.json on the server.")
    print("Handing off to GitHub Actions to commit and push the file to the repository...")

except Exception as e:
    print(f"FAILED: Python could not write the file. Error: {e}")
