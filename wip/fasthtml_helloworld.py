from fasthtml.common import *

# Initialize the FastHTML application
app, rt = fast_app()

# Define a route for the home page
@rt("/")
def get():
    # Return a titled page with a simple "Hello, World!" message
    return Titled("Hello World", P("Hello, World!"))

# Start the server
serve()

