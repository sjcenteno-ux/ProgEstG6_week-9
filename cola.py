def is_empty(queue):
    """Indica si la cola está vacía."""
    return len(queue) == 0


def is_full(queue, capacity):
    """Indica si la cola alcanzó su capacidad."""
    return len(queue) >= capacity


def enqueue(queue, item, capacity):
    """Agrega un elemento al final de la cola."""
    if is_full(queue, capacity):
        raise ValueError("La cola está llena.")

    queue.append(item)


def dequeue(queue):
    """Elimina y devuelve el primer elemento."""
    if is_empty(queue):
        raise ValueError("La cola está vacía.")

    return queue.pop(0)


def front(queue):
    """Consulta el primer elemento sin eliminarlo."""
    if is_empty(queue):
        raise ValueError("La cola está vacía.")

    return queue[0]


def show_queue(queue):
    """Devuelve una copia en orden de llegada."""
    return queue.copy()