history = []
current_page = None

def visit(page):
    global current_page
    if current_page is not None:
        history.append(current_page)

    current_page = page

    print(f"Visitar: {current_page}")

def go_back():
    global current_page

    if len(history) > 0:
        current_page = history.pop()
        print(f"Regresar -> {current_page}")

    else:
        print("Regresar -> sin anterior")

def show_current():
    if current_page is None:
        print("No hay pagina actual.")
    else:
        print(f"Pagina actual: {current_page}")

def show_history():
    if len(history) == 0:
        print("Historial vacio.")
    else:
        print("Historial:")
        for page in reversed(history):
            print(page)

while True:
    print("=== HISTORIAL DE NAVEGACION ===")
    print("1. Visitar pagina")
    print("2. Regresar")
    print("3. Mostrar pagina actual")
    print("4. Mostrar historial")
    print("5. Salir")

    try:
        option = int(input("Seleccione una opcion: "))

        if option == 1:
            page = input("Ingrese la pagina que desea visitar: ")
            visit(page)

        elif option == 2:
            go_back()

        elif option == 3:
            show_current()

        elif option == 4:
            show_history()

        elif option == 5:
            print("Programa finalizado.")
            break

        else:
            print("Debe seleccionar una opcion entre 1 y 5.")

    except ValueError:
        print("Debe ingresar un numero.")