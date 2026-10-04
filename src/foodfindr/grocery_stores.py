import os
from apify_client import ApifyClient

ACTOR_ID = "sunny_eternity/canada-grocery-price-comparison"


def get_grocery_prices_by_location(ingredients, postal_code):
    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise RuntimeError("Set the APIFY_TOKEN environment variable first.")

    client = ApifyClient(token)

    run_input = {
        "queries": ingredients,
        "postal_code": postal_code,
        "retailers": ["walmart", "loblaws", "sobeys", "metro", "costco"],
    }

    run = client.actor(ACTOR_ID).call(run_input=run_input)

    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        results.append({
            "store": item.get("retailer"),
            "ingredient": item.get("query"),
            "product_name": item.get("name"),
            "price": item.get("price"),
            "url": item.get("source_url"),
            # Store location fields, if the actor returns them:
            "store_address": item.get("store_address"),
            "store_name": item.get("store_name"),
        })

    return results


def cheapest_per_ingredient(results):
    best = {}
    for r in results:
        if r["price"] is None:
            continue
        cur = best.get(r["ingredient"])
        if cur is None or r["price"] < cur["price"]:
            best[r["ingredient"]] = r
    return best


if __name__ == "__main__":
    postal_code = input("Enter your postal code: ")
    ingredients = ["milk", "eggs", "chicken breast"]  # or from get_meals_by_ingredients
    results = get_grocery_prices_by_location(ingredients, postal_code)

    for ingredient, r in cheapest_per_ingredient(results).items():
        print(f"{ingredient}: ${r['price']} at {r['store']} ({r['product_name']})")