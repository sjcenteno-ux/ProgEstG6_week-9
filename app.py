import base64
import binascii
import os
import secrets

from io import BytesIO
from pathlib import Path
from uuid import uuid4

from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from PIL import Image, UnidentifiedImageError

from cola import (
    dequeue,
    enqueue,
    front,
    is_full,
    show_queue,
)


app = Flask(__name__)

app.config["SECRET_KEY"] = (
    os.environ.get("SECRET_KEY") or secrets.token_hex(32)
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024

MAX_CAPACITY = 12

PHOTO_FOLDER = Path(app.instance_path) / "fotos_cola"
PHOTO_FOLDER.mkdir(parents=True, exist_ok=True)


def photo_info(filename):
    """Prepara los datos de una fotografía para JavaScript."""
    if filename is None:
        return None

    return {
        "id": filename,
        "url": url_for("photo_file", filename=filename),
    }


def queue_state():
    """Devuelve el estado actual de la cola."""
    queue = session.get("queue_photos", [])
    capacity = session.get("queue_capacity")

    return {
        "active": capacity is not None,
        "capacity": capacity,
        "items": [
            photo_info(filename)
            for filename in show_queue(queue)
        ],
        "last": photo_info(session.get("queue_last")),
    }


def save_photo(data_url):
    """Comprueba una fotografía y la guarda como JPEG."""
    prefix = "data:image/jpeg;base64,"

    if not isinstance(data_url, str):
        raise ValueError("La fotografía no es válida.")

    if not data_url.startswith(prefix):
        raise ValueError("Primero toma o selecciona una fotografía.")

    try:
        image_bytes = base64.b64decode(
            data_url[len(prefix):],
            validate=True,
        )
    except (binascii.Error, ValueError):
        raise ValueError("La fotografía está dañada.") from None

    if len(image_bytes) > 2 * 1024 * 1024:
        raise ValueError("La fotografía es demasiado grande.")

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if image.format != "JPEG":
                raise ValueError("Se esperaba una fotografía JPEG.")

            if image.width > 1920 or image.height > 1920:
                raise ValueError("La resolución es demasiado grande.")

            image.load()
            photo = image.convert("RGB")
            photo.thumbnail((640, 640))

    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
    ):
        raise ValueError("No se pudo leer la imagen.") from None

    filename = f"{uuid4().hex}.jpg"
    photo.save(PHOTO_FOLDER / filename, "JPEG", quality=85)

    return filename


def delete_photo(filename):
    """Elimina una fotografía del disco, si existe."""
    if filename:
        (PHOTO_FOLDER / filename).unlink(missing_ok=True)


@app.route("/")
def index():
    if "queue_csrf" not in session:
        session["queue_csrf"] = secrets.token_hex(32)

    return render_template(
        "index.html",
        csrf_token=session["queue_csrf"],
        max_capacity=MAX_CAPACITY,
    )


@app.route("/foto-cola/<filename>")
def photo_file(filename):
    """Entrega una foto de la cola o la última atendida."""
    allowed = list(session.get("queue_photos", []))

    last = session.get("queue_last")

    if last:
        allowed.append(last)

    if filename not in allowed:
        abort(404)

    response = send_from_directory(
        str(PHOTO_FOLDER),
        filename,
    )

    response.headers["Cache-Control"] = "no-store"

    return response


@app.route("/api/cola", methods=["GET", "POST"])
def queue_api():
    if request.method == "GET":
        response = jsonify(state=queue_state())
        response.headers["Cache-Control"] = "no-store"
        return response

    expected = session.get("queue_csrf")
    received = request.headers.get("X-CSRF-Token", "")

    if not expected or not secrets.compare_digest(
        received,
        expected,
    ):
        return jsonify(
            error="La sesión cambió. Actualiza la página."
        ), 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="La solicitud no es válida."), 400

    action = data.get("action")

    queue = list(session.get("queue_photos", []))
    capacity = session.get("queue_capacity")

    try:
        if action == "create":
            if capacity is not None:
                raise ValueError("Primero reinicia la cola.")

            new_capacity = data.get("capacity")

            if (
                type(new_capacity) is not int
                or not 1 <= new_capacity <= MAX_CAPACITY
            ):
                raise ValueError(
                    f"La capacidad debe estar entre 1 y {MAX_CAPACITY}."
                )

            session["queue_capacity"] = new_capacity
            session["queue_photos"] = []
            session.pop("queue_last", None)

            message = "Cola creada. Ya puedes agregar fotografías."

        elif capacity is None:
            raise ValueError("Primero crea una cola.")

        elif action == "enqueue":
            if is_full(queue, capacity):
                raise ValueError(
                    "La cola está llena. Atiende una foto para liberar espacio."
                )

            filename = save_photo(data.get("photo", ""))

            enqueue(queue, filename, capacity)
            session["queue_photos"] = queue

            message = "Fotografía agregada al final de la cola."

        elif action == "dequeue":
            # Comprobamos que exista un frente antes de cambiar archivos.
            front(queue)

            # Conservamos únicamente la última foto atendida.
            delete_photo(session.get("queue_last"))

            filename = dequeue(queue)

            session["queue_photos"] = queue
            session["queue_last"] = filename

            message = (
                "Se atendió la primera fotografía. "
                "Puedes verla en el panel de última atendida."
            )

        elif action == "front":
            front(queue)

            message = (
                "La fotografía marcada como 'Siguiente' está al frente. "
                "La cola no cambió."
            )

        elif action == "reset":
            for filename in queue:
                delete_photo(filename)

            delete_photo(session.get("queue_last"))

            session.pop("queue_photos", None)
            session.pop("queue_capacity", None)
            session.pop("queue_last", None)

            message = "Cola reiniciada."

        else:
            raise ValueError("Operación desconocida.")

    except ValueError as error:
        return jsonify(error=str(error)), 400

    except OSError:
        return jsonify(
            error="No se pudo guardar o eliminar la imagen en disco."
        ), 500

    return jsonify(
        message=message,
        state=queue_state(),
    )


@app.errorhandler(413)
def too_large(error):
    return jsonify(
        error="La imagen enviada es demasiado grande."
    ), 413