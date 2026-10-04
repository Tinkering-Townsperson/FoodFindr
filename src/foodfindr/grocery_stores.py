import os
import json
from apify_client import ApifyClient

# Optional: loads APIFY_TOKEN from a .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ACTOR_ID = "sunny_eternity/canada-grocery-price-comparison"


def get_grocery_prices_by_location(ingredients, postal_code):
    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise RuntimeError("Set the APIFY_TOKEN environment variable first.")

    client = ApifyClient(token)

    results = []
    raw_items = []

    # Free Apify plan only uses the first 5 queries per run, so send batches of 5
    for start in range(0, len(ingredients), 5):
        batch = ingredients[start:start + 5]

        run_input = {
            "queries": batch,
            "postal_code": postal_code,
            "retailers": ["superstore", "saveonfoods", "pricesmart", "urbanfare", "tnt", "loblaws"],
            "maxResultsPerQueryPerRetailer": 3,
            "minMatchConfidence": "low",
            "outputMode": "comparison",
        }

        run = client.actor(ACTOR_ID).call(run_input=run_input)

        for item in client.dataset(run.default_dataset_id).iterate_items():
            raw_items.append(item)

            if "basket_summary" in item or "run_meta" in item:
                continue

            query_name = item.get("query") or item.get("searchQuery") or item.get("search_term")
            if not query_name:
                continue

            raw_price = item.get("price") or item.get("sale_price")
            try:
                price = float(raw_price) if raw_price is not None else None
            except (ValueError, TypeError):
                price = None

            results.append({
                "store": item.get("retailer") or item.get("company"),
                "ingredient": str(query_name).strip().lower(),
                "product_name": item.get("name") or item.get("matched_product"),
                "price": price,
                "url": item.get("source_url") or item.get("url"),
            })

    # Save the raw output so you can inspect the real field names
    with open("price_cache.json", "w") as f:
        json.dump(raw_items, f, indent=2)

    print(f"Raw items: {len(raw_items)}, parsed with a query name: {len(results)}")
    return results


def top_three_per_ingredient(results):
    by_ingredient = {}
    for r in results:
        if r["price"] is None:
            continue
        by_ingredient.setdefault(r["ingredient"], []).append(r)

    ranked = {}
    for ingredient, items in by_ingredient.items():
        items.sort(key=lambda x: x["price"])  # cheapest first
        ranked[ingredient] = items[:3]
    return ranked


if __name__ == "__main__":
    postal_code = input("Enter your Canadian postal code (e.g. V5H 1A1): ").strip()
    raw = input("Enter the ingredients you need (separated by commas): ")
    ingredients = [i.strip().lower() for i in raw.split(",") if i.strip()]

    if not ingredients:
        print("You didn't enter any ingredients.")
    else:
        results = get_grocery_prices_by_location(ingredients, postal_code)
        ranked = top_three_per_ingredient(results)

        for ingredient, top in ranked.items():
            print(f"\n{ingredient}")
            for rank, r in enumerate(top, start=1):
                print(f"  {rank}. ${r['price']:.2f} - {r['store']} ({r['product_name']})")

        not_found = [i for i in ingredients if i not in ranked]
        print("\nNo prices found for:", ", ".join(not_found) or "none")
