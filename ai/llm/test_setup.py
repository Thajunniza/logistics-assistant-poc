import os
import litellm
from dotenv import load_dotenv

# 1. Force Python to read and inject the variables from your .env file
load_dotenv()

# 2. Enable debug logging to watch the SAP OAuth handshake/routing
os.environ["LITELLM_LOG"] = "DEBUG"

individual_vars = [
    "AICORE_AUTH_URL", 
    "AICORE_CLIENT_ID", 
    "AICORE_CLIENT_SECRET", 
    "AICORE_BASE_URL", 
    "AICORE_RESOURCE_GROUP"
]

print("=== SAP Gen AI Hub Setup Verification ===\n")

# Check for service key method vs individual variables
if os.environ.get("AICORE_SERVICE_KEY"):
    print("✓ Using AICORE_SERVICE_KEY authentication (includes resource group)")
else:
    missing = [v for v in individual_vars if not os.environ.get(v)]
    if missing:
        print(f"✗ Missing environment variables in memory: {missing}")
        print("👉 Tip: Make sure your .env file is in the same folder where you run the script.")
    else:
        print("✓ Using individual variable authentication")
        print(f"✓ Resource group: {os.environ.get('AICORE_RESOURCE_GROUP')}")

# Test API connection
print("\n=== Testing API Connection ===\n")
try:
    # IMPORTANT: Ensure 'sap/gpt-4o' matches the deployment ID or config 
    # mapped in your SAP AI Launchpad/Hub resource group.
    response = litellm.completion(
        model="sap/gpt-4o",
        messages=[{"role": "user", "content": "Say 'Connection successful!' and nothing else."}],
        max_tokens=20
    )
    print(f"✓ API Response: {response.choices[0].message.content}")
    print("\n🎉 Setup complete! You're ready to use SAP Gen AI Hub with LiteLLM.")
except Exception as e:
    print(f"✗ API Error: {e}")
    print("\nTroubleshooting tips:")
    print("  1. Verify your service key credentials are correct")
    print("  2. Check that your deployment ID or model tag matches 'gpt-4o'")
    print("  3. Ensure your SAP AI Core instance is running and has available quota")
