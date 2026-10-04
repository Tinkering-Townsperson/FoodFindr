import requests
from dotenv import load_dotenv
import os
load_dotenv()
def find_nearby_food(food, postal_code):
    # Use the Instacart API to find nearby grocery stores that sell the specified food
    api_key = os.getenv("INSTACART_API_KEY")
    url = f"https://api.instacart.com/v1/stores/search?query={food}&postal_code={postal_code}&api_key={api_key}"

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        stores = data.get("stores")
        if stores:
            print(f"Found {len(stores)} stores that sell '{food}' near postal code '{postal_code}':")
            for store in stores:
                print(f"- {store['name']} ({store['address']})")
        else:
            print(f"No stores found that sell '{food}' near postal code '{postal_code}'.")
find_nearby_food("milk", "10001")