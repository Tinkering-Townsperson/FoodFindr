from itertools import takewhile
import requests

# API

ingredients = []
meal_names = []
user_input = input(" Enter your ingredients: ")
ingredients.extend([i.strip() for i in user_input.split(",") if i.strip()])

#print(ingredients)

def get_meals_by_ingredients(ingredients):
    # print(url)
    # print(response.status_code)
    if len(ingredients) > 1:
        for ingredient in ingredients:
            url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient.strip()}"
            
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                meals = data.get("meals")
                if meals:
                    # print(f"Found {len(meals)} meals with the ingredients '{ingredients}':")
                    for meal in meals:
                        url2 = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal['idMeal']}"
                        response2 = requests.get(url2)      
                        # print(f"- {meal['strMeal']}")
                        meal_ingrediients = response2.json().get("meals")[0]
                        meal_ingredients_list = [meal_ingrediients[f"strIngredient{i}"] for i in range(1, 21) if meal_ingrediients[f"strIngredient{i}"]]
                        meal_ingredients_set = set([ingredient.lower() for ingredient in takewhile(lambda i: i not in ("", None), meal_ingredients_list)])

                        if all(
                            any(ingredient.strip().lower() in recipe_ing for recipe_ing in meal_ingredients_set)
                            for user_ing in ingredients
                        ):
                        # print(f"Ingredients: {', '.join(meal_ingredients_set)}")
                            if meal['strMeal'] not in meal_names:
                                meal_names.append(meal['strMeal'])
                        
                else:
                    print(f"No meals found with the ingredients '{ingredients}'.")
    print(meal_names)

get_meals_by_ingredients(ingredients)


    
        
  