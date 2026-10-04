import json
import os
import random
import re
from collections.abc import Iterator
from pathlib import Path

import requests
import sseclient

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


API_ENDPOINT = "/api/v2/cortex/inference:complete"
MODEL_NAME = "claude-sonnet-4-6"
MEALDB_KEY = os.getenv("MEALDB_API_KEY", "1")
MEALDB_BASE = f"https://www.themealdb.com/api/json/v1/{MEALDB_KEY}"

PREMADE_PROMPTS = {
    "Chicken & rice": {"prompt": "chicken, rice"},
    "Vegetarian ideas": {"prompt": "Show me vegetarian recipes", "category": "Vegetarian"},
    "Seafood dinner": {"prompt": "Show me seafood recipes", "category": "Seafood"},
    "Something sweet": {"prompt": "Show me dessert recipes", "category": "Dessert"},
    "Breakfast ideas": {"prompt": "Show me breakfast recipes", "category": "Breakfast"},
    "Shopping list": {"prompt": "Make me a shopping list for the recipes above"},
}

URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
BLOCKED_RE = re.compile(r"(instagram|tik[\s_-]?tok)", re.IGNORECASE)


def clean_text(text: str) -> str:
    return BLOCKED_RE.sub("", URL_RE.sub("", text))


def filter_stream(chunks: Iterator[str]) -> Iterator[str]:
    """Clean the model reply as it streams, one whole word at a time."""
    buf = ""
    for chunk in chunks:
        buf += chunk
        cut = max(buf.rfind(" "), buf.rfind("\n"))
        if cut != -1:
            yield clean_text(buf[: cut + 1])
            buf = buf[cut + 1 :]
    if buf:
        yield clean_text(buf)


def find_recipes(ingredients: str, max_results: int = 3, category: str | None = None) -> str:
    """Search TheMealDB and return matching recipes as JSON."""
    counts: dict[str, int] = {}
    total = 1

    if category:
        try:
            response = requests.get(
                f"{MEALDB_BASE}/filter.php", params={"c": category}, timeout=10
            )
            response.raise_for_status()
            meals = response.json().get("meals") or []
        except requests.RequestException:
            meals = []
        for meal in random.sample(meals, min(max_results, len(meals))):
            counts[meal["idMeal"]] = 1
    else:
        items = [item.strip().lower().replace(" ", "_") for item in ingredients.split(",") if item.strip()]
        total = len(items)
        for item in items:
            try:
                response = requests.get(
                    f"{MEALDB_BASE}/filter.php", params={"i": item}, timeout=10
                )
                response.raise_for_status()
                meals = response.json().get("meals") or []
            except requests.RequestException:
                continue
            for meal in meals:
                counts[meal["idMeal"]] = counts.get(meal["idMeal"], 0) + 1

    recipes = []
    for meal_id in sorted(counts, key=counts.get, reverse=True)[:max_results]:
        try:
            response = requests.get(
                f"{MEALDB_BASE}/lookup.php", params={"i": meal_id}, timeout=10
            )
            response.raise_for_status()
            meal = response.json()["meals"][0]
        except (requests.RequestException, KeyError, IndexError, TypeError):
            continue

        if BLOCKED_RE.search(json.dumps(meal)):
            continue

        ingredients_list = []
        for number in range(1, 21):
            ingredient = (meal.get(f"strIngredient{number}") or "").strip()
            if ingredient:
                measure = (meal.get(f"strMeasure{number}") or "").strip()
                ingredients_list.append(f"{measure} {ingredient}".strip())

        recipes.append(
            {
                "name": meal["strMeal"],
                "category": meal.get("strCategory"),
                "cuisine": meal.get("strArea"),
                "ingredients": ingredients_list,
                "instructions": clean_text(meal.get("strInstructions") or "")[:1500],
                "matches": (
                    f"{category} recipe"
                    if category
                    else f"{counts[meal_id]} of {total} searched ingredients"
                ),
            }
        )

    return json.dumps(recipes) if recipes else ""


def stream_model(messages: list[dict[str, str]], connection) -> Iterator[str]:
    """Send messages to Snowflake Cortex and yield the reply as it streams."""
    response = requests.post(
        url=f"https://{connection.host}{API_ENDPOINT}",
        json={
            "model": MODEL_NAME,
            "messages": messages,
            "top_p": 0,
            "temperature": 0,
            "stream": True,
        },
        headers={
            "Authorization": f'Snowflake Token="{connection.rest.token}"',
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        stream=True,
        timeout=50,
    )
    response.raise_for_status()

    client = sseclient.SSEClient(response)
    for event in client.events():
        try:
            parsed = json.loads(event.data)
        except (TypeError, json.JSONDecodeError):
            continue
        choices = parsed.get("choices") or []
        if choices:
            delta = choices[0].get("delta", {})
            text = delta.get("content") or delta.get("text") or ""
            if text:
                yield text


def extract_ingredients(history: list[dict[str, str]], connection) -> str:
    recent = history[-5:]
    transcript = "\n".join(f"{message['role']}: {message['content'][:300]}" for message in recent)
    messages = [
        {
            "role": "system",
            "content": (
                "Extract the food ingredients the user wants to cook with. Use earlier "
                "messages when the latest refers back to them. Reply with ONLY a comma-separated "
                "list of ingredient names in lowercase singular English, or exactly NONE."
            ),
        },
        {"role": "user", "content": transcript},
    ]
    text = "".join(stream_model(messages, connection)).strip()
    if not text or text.upper().startswith("NONE"):
        return ""
    return text.splitlines()[0][:200]


def api_call(
    prompt: str,
    history: list[dict[str, str]],
    connection,
    category: str | None = None,
) -> Iterator[str]:
    ingredients = ""
    if category:
        recipes = find_recipes("", category=category)
    else:
        ingredients = extract_ingredients(history, connection)
        recipes = find_recipes(ingredients) if ingredients else ""

    if recipes and category:
        system = (
            "You are FoodFindr's friendly recipe assistant. Recommend recipes using ONLY "
            "the recipe data below. For each one, give the name, a short ingredient list with "
            "quantities, and short steps. Do not invent recipes.\n\nRECIPE DATA:\n" + recipes
        )
    elif recipes:
        system = (
            "You are FoodFindr's friendly recipe assistant. The user has these ingredients: "
            + ingredients
            + ". They have ONLY those ingredients plus basic pantry items (water, salt, "
            "pepper, cooking oil). Start from the recipes in RECIPE DATA and adapt each one "
            "so it uses only what the user has. Drop optional ingredients, use sensible swaps "
            "only when available, and say when a recipe is not a good fit. Include quantities, "
            "short steps, and changes from the original. Do not add ingredients.\n\nRECIPE DATA:\n"
            + recipes
        )
    else:
        system = (
            "You are FoodFindr's friendly recipe assistant. Chat naturally and help with "
            "cooking questions. If the user asks for recipes without ingredients, ask which "
            "ingredients they have. If ingredients do not match, say no matching recipes were "
            "found in the database. Do not present invented recipes as database recipes."
        )

    system += (
        "\n\nNever include links or URLs. Never mention social media or video platforms. "
        "If the user asks for a shopping list, list missing non-pantry ingredients with their "
        "recipe quantities, grouped by recipe. If a quantity is missing, write 'amount not "
        "specified' instead of guessing."
    )
    usable_history = history[-6:]
    messages = [{"role": "system", "content": system}] + usable_history + [
        {"role": "user", "content": prompt}
    ]
    yield from stream_model(messages, connection)


def snowflake_settings() -> dict[str, str]:
    secrets_path = Path(__file__).with_name(".streamlit") / "secrets.toml"
    file_secrets = {}
    if secrets_path.is_file():
        with secrets_path.open("rb") as secrets_file:
            file_secrets = tomllib.load(secrets_file).get("snowflake", {})

    values = {
        "user": os.getenv("SNOWFLAKE_USER") or file_secrets.get("user"),
        "password": os.getenv("SNOWFLAKE_API_KEY") or file_secrets.get("api_key"),
        "account": os.getenv("SNOWFLAKE_ACCOUNT") or file_secrets.get("account"),
        "host": os.getenv("SNOWFLAKE_HOST") or file_secrets.get("host"),
        "role": os.getenv("SNOWFLAKE_ROLE") or file_secrets.get("role"),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing Snowflake environment variables: "
            + ", ".join(
                {
                    "user": "SNOWFLAKE_USER",
                    "password": "SNOWFLAKE_API_KEY",
                    "account": "SNOWFLAKE_ACCOUNT",
                    "host": "SNOWFLAKE_HOST",
                    "role": "SNOWFLAKE_ROLE",
                }[name]
                for name in missing
            )
        )
    return values
