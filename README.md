# FoodFindr
Our project for StormHacks 2026. List ingredients you have, and find recipes that incorporate them. Lacking ingredients you need? Find where to purchase them for the cheapest price close by!

## Run the Flask app

Install the project dependencies, set the Snowflake variables, and start Flask:

```powershell
poetry install
$env:FLASK_SECRET_KEY = "replace-with-a-random-secret"
$env:SNOWFLAKE_USER = "your-user"
$env:SNOWFLAKE_API_KEY = "your-api-key"
$env:SNOWFLAKE_ACCOUNT = "your-account"
$env:SNOWFLAKE_HOST = "your-account.snowflakecomputing.com"
$env:SNOWFLAKE_ROLE = "your-role"
poetry run foodfindr
```

The recipe search is available at `/`, and the Flask chat is available at `/chat`.
The chat uses the Snowflake API key as the Snowflake connector password. Do not commit
credentials or put them in source control. For local development, Flask also reads the
`[snowflake]` section from `src/foodfindr/.streamlit/secrets.toml`; environment variables
override values from that file. The `.streamlit` directory is not special to Flask—the
application reads this file explicitly.
