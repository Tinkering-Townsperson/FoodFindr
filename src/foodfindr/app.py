import os

import requests
import snowflake.connector
from flask import Flask, flash, redirect, render_template, request, session, url_for

from foodfindr.chat import PREMADE_PROMPTS, api_call, filter_stream, snowflake_settings
from foodfindr.get_meals import get_meals_by_ingredients


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "development-only-change-me")


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


@app.route('/cart')
def cart():
    return render_template('cart.html', title='Ingredient Cart')


@app.route('/chat', methods=['GET', 'POST'])
def chat():
    messages = session.setdefault(
        "chat_messages",
        [
            {
                "role": "assistant",
                "content": "Hi! I'm FoodFindr's recipe assistant. Type ingredients separated by commas or choose a quick start.",
            }
        ],
    )

    if request.method == "POST":
        if request.form.get("action") == "clear":
            session.pop("chat_messages", None)
            return redirect(url_for("chat"))

        prompt = request.form.get("prompt", "").strip()
        category = request.form.get("category") or None
        if prompt:
            messages.append({"role": "user", "content": prompt})
            connection = None
            try:
                connection = snowflake.connector.connect(
                    **snowflake_settings(), port=443
                )
                response = "".join(
                    filter_stream(api_call(prompt, messages[:-1], connection, category))
                )
                messages.append({"role": "assistant", "content": response})
                session["chat_messages"] = messages
            except (requests.RequestException, RuntimeError, snowflake.connector.errors.Error) as error:
                flash(f"Chat is unavailable: {error}", "error")
                messages.pop()
                session["chat_messages"] = messages
            finally:
                if connection is not None:
                    connection.close()

    return render_template(
        "chat.html",
        title="Chat",
        messages=messages,
        premade_prompts=PREMADE_PROMPTS,
    )


def runapp():
    app.run(debug=True)


if __name__ == '__main__':
    runapp()
