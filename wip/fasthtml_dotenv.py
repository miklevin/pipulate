from fasthtml.common import *
from dotenv import load_dotenv, set_key
import os

# Initialize the FastHTML application
app, rt = fast_app()

# Load environment variables
load_dotenv()

@rt("/")
def get():
    # Reload the environment variables to reflect any updates
    load_dotenv()
    secret = os.getenv('SECRET')
    if secret:
        message = P("I already know your secret")
    else:
        message = Form(method="post")(
            Label("Enter the secret:", Input(type="password", name="secret")),
            Button("Submit", type="submit")
        )
    return Titled("Secret Prompt", message)

@rt("/", methods=["POST"])
def post(secret: str):
    # Save the secret to the .env file if it hasn't been set
    if not os.getenv('SECRET'):
        set_key('.env', 'SECRET', secret)
        load_dotenv()  # Reload the .env file after updating it
        return Titled("Secret Saved", P("Your secret has been saved."))
    else:
        return Titled("Secret Already Set", P("A secret is already set. No changes were made."))

# Start the server
serve()
