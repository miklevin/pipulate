from fasthtml.common import *

def render(todo):
    return Li(todo.title)

app, rt, todos, Todo = fast_app("todo.db", live=True, render=render,
                                id=int, title=str, done=bool, pk="id")

@rt("/")
def get():

    todos.insert(Todo(title='Todo per page-load', done=False))

    return Titled('Todos', 
                  Ul(*todos()),
                )

serve()

