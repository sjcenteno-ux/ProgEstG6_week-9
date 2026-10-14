stack = []
capacity = 5

def isEmpty():
    return not len(stack)

def is_full(capacity):
    return len(stack) == capacity


def push(item, capacity):
    if item in stack:
        return "La caja ya se encuentra registrada."

    if not is_full(capacity):
        stack.append(item)
        return "Caja apilada correctamente."

    return "Pila llena."

def peek():
    if not isEmpty():
        return stack[-1]

    return "Pila vacia."

def pop_stack():
    if not isEmpty():
        return stack.pop()

    return "Pila vacia."


def llenarPila():
    while True:

        if is_full(capacity):
            print("La pila ya tiene las 5 cajas.")
            break

        item = input("Ingrese el codigo de la caja: ")

        if item == "":
            print("El codigo no puede estar vacio.")
        else:
            print(push(item, capacity))

        answer = input("Desea ingresar otra caja [S | N]: ")

        if answer.lower() == "n":
            break


def desapilar():
    while True:
        if isEmpty():
            print("La pila esta vacia.")
            break

        answer = input("Desea desapilar [S | N]: ")

        if answer.lower() == "s":
            print(f"Caja retirada: {pop_stack()}")

        elif answer.lower() == "n":
            break

        else:
            print("Opcion invalida.")


def showStack():
    if isEmpty():
        return "Pila vacia."

    message = ""

    for item in reversed(stack):
        message += f"| {item:>6} |\n"
        message += "*" + "-" * 8 + "*\n"

    message += f"Cantidad de cajas: {len(stack)}"

    return message


while True:

    print("=== CONTROL DE CAJAS EN BODEGA ===")
    print("1. Apilar cajas")
    print("2. Desapilar cajas")
    print("3. Consultar tope")
    print("4. Mostrar pila de cajas")
    print("5. Salir")

    try:
        option = int(input("Seleccione una opcion: "))

        if option == 1:
            llenarPila()

        elif option == 2:
            desapilar()

        elif option == 3:
            print(f"Tope de la pila: {peek()}")

        elif option == 4:
            print(showStack())

        elif option == 5:
            print("Programa finalizado.")
            break

        else:
            print("Debe ingresar una opcion entre 1 y 5.")

    except ValueError:
        print("Debe ingresar un numero.")