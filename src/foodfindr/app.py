from flask import Flask, render_template, request

from foodfindr.get_meals import get_meals_by_ingredients


app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    ingredients = []
    meals = []

    if request.method == 'POST':
        ingredients = [
            ingredient.strip().lower()
            for ingredient in request.form.get('ingredients', '').split(',')
            if ingredient.strip()
        ]

        full_meals, partial_meals = get_meals_by_ingredients(ingredients)
        meals_by_id = {meal.id: meal for meal in full_meals + partial_meals}
        provided_ingredients = set(ingredients)
        meals = sorted(
            meals_by_id.values(),
            key=lambda meal: len(meal.ingredients & provided_ingredients),
            reverse=True,
        )

    return render_template(
        'index.html',
        title='Home',
        ingredients=ingredients,
        meals=meals,
    )


def runapp():
    app.run(debug=True)


if __name__ == '__main__':
    runapp()
