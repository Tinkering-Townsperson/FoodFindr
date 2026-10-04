from itertools import takewhile
from meal import Meal
import requests

# API
MAX_MISSING_INGREDIENTS = -1


def get_meals_by_ingredients(ingredients):
    partial_meal_names = []
    full_meal_names = []

    if not ingredients:
        return [], []

    for ingredient in ingredients:
        url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient.strip()}"

        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        meals = data.get("meals")
        if meals:
            for meal in meals[:8]:
                meal_data = requests.get(f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal['idMeal']}")
                meal_data.raise_for_status()
                meal_ingredients = meal_data.json().get("meals")[0]
                meal_ingredients_list = [
                    meal_ingredients[f"strIngredient{i}"]
                    for i in range(1, 21)
                    if meal_ingredients[f"strIngredient{i}"]
                ]
                meal_ingredients_set = {
                    ingredient.lower()
                    for ingredient in takewhile(
                        lambda i: i not in ("", None), meal_ingredients_list
                    )
                }
                recipe = meal_ingredients.get('strInstructions', '')

                # Look for meals that can be made with given ingredients, with no missing ingredients
                if len(meal_ingredients_set - set([ingredient.lower() for ingredient in ingredients])) == 0:
                    full_meal_names.append(
                        Meal(
                            name=meal['strMeal'],
                            id=meal['idMeal'],
                            recipe=recipe,
                            ingredients=meal_ingredients_set,
                        )
                    )

                # Look for meals in which the number of missing ingredients is less than or equal to MAX_MISSING_INGREDIENTS
                missing_ingredients = meal_ingredients_set - set([ingredient.lower() for ingredient in ingredients])
                if len(missing_ingredients) <= MAX_MISSING_INGREDIENTS or MAX_MISSING_INGREDIENTS < 0:
                    partial_meal_names.append(
                        Meal(
                            name=meal['strMeal'],
                            id=meal['idMeal'],
                            recipe=recipe,
                            ingredients=meal_ingredients_set,
                        )
                    )
        else:
            print(f"No meals found with the ingredients '{ingredients}'.")
    return full_meal_names, partial_meal_names


if __name__ == "__main__":
    user_ingredients = []
    # Full meal names are meals that can be made with the given ingredients, with no missing ingredients
    # Partial meal names allow missing ingredients up to MAX_MISSING_INGREDIENTS.
    user_input = input(" Enter your ingredients: ")
    user_ingredients.extend(user_input.split(","))

    print(user_ingredients)
    m: tuple[list[Meal]] = get_meals_by_ingredients(user_ingredients)
    print(m[0].recipe)
