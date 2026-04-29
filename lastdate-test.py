import sys
import json
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "custom_components", "shlabs_sabiana_wifi"))
from lastdate_decoder import SabianaCloudWM

def run_test():
    # 1. Check for command line argument
    if len(sys.argv) < 2:
        print("Usage: python3 test_decoder.py <hex_string>")
        return

    hex_input = sys.argv[1]
    
    # 2. Call the reusable logic
    result = SabianaCloudWM.parse(hex_input)

    # 3. Handle Errors
    if "error" in result:
        print(f"FAILED: {result['error']}")
        return

    # 4. Pretty-print the resulting object
    print("\n--- DECODED SABIANA OBJECT ---")
    # Using json.dumps makes the dictionary look like a clean JSON object
    print(json.dumps(result, indent=4))
    print("------------------------------\n")

if __name__ == "__main__":
    run_test()