from itertools import takewhile
import requests

# API

MAX_MISSING_INGREDIENTS = 3

ingredients = []
#Full meal names are meals that can be made with the given ingredients, with no missing ingredients
#Partial meal names are meals that can be made with the given ingredients, with missing ingredients less than or equal to MAX_MISSING_INGREDIENTS
full_meal_names = []
partial_meal_names = []
user_input = input(" Enter your ingredients: ")
ingredients.extend(user_input.split(","))

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
                        # Look for meals that can be made with given ingredients, with no missing ingredients

                        if len(meal_ingredients_set - set([ingredient.lower() for ingredient in ingredients])) == 0:
                            # print(f"Ingredients: {', '.join(meal_ingredients_set)}")
                            full_meal_names.append(meal['strMeal'])

                        # Look for meals in which the number of missing ingredients is less than or equal to MAX_MISSING_INGREDIENTS
                        missing_ingredients = meal_ingredients_set - set([ingredient.lower() for ingredient in ingredients])
                        if len(missing_ingredients) <= MAX_MISSING_INGREDIENTS:
                            # print(f"Ingredients: {', '.join(meal_ingredients_set)}")
                            partial_meal_names.append(meal['strMeal'])
                        return full_meal_names, partial_meal_names
                else:
                    print(f"No meals found with the ingredients '{ingredients}'.")

get_meals_by_ingredients(ingredients)




    
        
  