from fasthtml.common import *


def render(todo):
    tid = f'todo-{todo.id}'
    checkbox = Input(type="checkbox", 
                     name="english" if todo.done else None, 
                     checked=todo.done,
                     hx_post=f"/toggle/{todo.id}",
                     hx_swap="outerHTML",
                     hx_target=f"#checkbox-{tid}")
    delete = A('Delete', hx_delete=f'/{todo.id}', 
               hx_swap='outerHTML', hx_target=f"#{tid}")
    return Li(Span(checkbox, id=f"checkbox-{tid}"), ' ', 
              todo.title,
              ' ', delete,
              id=tid, cls='done' if todo.done else '')


app, rt, todos, Todo = fast_app("data/todo.db", live=True, render=render,
                                id=int, title=str, done=bool, pk="id")


def mk_input(): 
    return Input(placeholder='Add a new item', 
                 id='title', 
                 hx_swap_oob='true',
                 style="border-color: var(--pico-primary);")


@rt('/')
def get():
    frm = Form(Group(mk_input(),
               Button('Add')),
               hx_post='/', target_id='todo-list', hx_swap="beforeend")
    return Titled('Todos', 
                  Card(
                  Ul(*todos(), id='todo-list'),
                  header=frm)
                )


@rt('/')
def post(todo:Todo): return todos.insert(todo), mk_input()


@rt('/{tid}')
def delete(tid:int): todos.delete(tid)
    

@rt('/toggle/{tid}')
def get(tid:int):
    todo = todos[tid]
    todo.done = not todo.done
    return todos.update(todo)


serve()

