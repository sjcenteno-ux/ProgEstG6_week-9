"use strict";

const $ = (selector) => document.querySelector(selector);

const csrfToken = $('meta[name="csrf-token"]').content;

const video = $("#camera");
const canvas = $("#canvas");

let stream = null;
let preparedPhoto = "";
let state = null;

let busy = false;
let capturing = false;
let loadingImage = false;


function notify(text, type = "info") {
  const notice = $("#notice");

  notice.className = `alert alert-${type}`;
  notice.textContent = text;
}


function updateButtons() {
  const active = Boolean(state?.active);
  const count = state?.items.length ?? 0;

  const full = active && count >= state.capacity;

  document.querySelectorAll("[data-action]").forEach((button) => {
    button.disabled = busy;
  });

  $("#enqueue").disabled =
    busy ||
    !active ||
    full ||
    !preparedPhoto ||
    capturing ||
    loadingImage;

  $("#dequeue").disabled = busy || !active || count === 0;
  $("#front").disabled = busy || !active || count === 0;

  $("#capture").disabled =
    !stream || capturing || busy || loadingImage;

  $("#upload").disabled = busy || capturing || loadingImage;
  $("#discard").disabled = busy || capturing || loadingImage;
}


function render(nextState) {
  state = nextState;

  $("#setup").hidden = state.active;
  $("#workspace").hidden = !state.active;

  if (!state.active) {
    updateButtons();
    return;
  }

  const count = state.items.length;

  $("#count").textContent = count;
  $("#available").textContent = state.capacity - count;
  $("#limit").textContent = state.capacity;

  const badge = $("#queue-status");

  if (count === 0) {
    badge.textContent = "Vacía";
    badge.className = "badge text-bg-secondary";

  } else if (count >= state.capacity) {
    badge.textContent = "Completa";
    badge.className = "badge text-bg-warning";

  } else {
    badge.textContent = "Recibiendo fotografías";
    badge.className = "badge text-bg-success";
  }

  $("#empty").hidden = count !== 0;

  const list = $("#queue-list");
  list.replaceChildren();

  state.items.forEach((item, index) => {
    const column = document.createElement("div");
    column.className = "col-12 col-sm-6";

    const card = document.createElement("article");
    card.className = index === 0
      ? "card h-100 border-primary border-2"
      : "card h-100";

    if (index === 0) {
      card.id = "front-card";
    }

    const image = document.createElement("img");
    image.src = item.url;
    image.alt = `Fotografía en la posición ${index + 1}`;
    image.className = "card-img-top";

    const body = document.createElement("div");
    body.className = "card-body";

    const label = document.createElement("span");
    label.className = index === 0
      ? "badge text-bg-primary"
      : "badge text-bg-secondary";

    label.textContent = index === 0
      ? "Siguiente · Frente"
      : `Posición ${index + 1}`;

    body.append(label);

    if (index === state.items.length - 1) {
      const end = document.createElement("p");
      end.className = "small text-body-secondary mt-2 mb-0";
      end.textContent = "Final de la cola";
      body.append(end);
    }

    card.append(image, body);
    column.append(card);
    list.append(column);
  });

  $("#last-empty").hidden = Boolean(state.last);
  $("#last-photo").hidden = !state.last;

  if (state.last) {
    $("#last-photo").src = state.last.url;
  } else {
    $("#last-photo").removeAttribute("src");
  }

  updateButtons();
}


async function loadState() {
  busy = true;
  updateButtons();

  try {
    const response = await fetch("/api/cola", {
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error("No se pudo cargar la cola.");
    }

    const result = await response.json();

    render(result.state);
    notify("Aplicación lista. Crea una cola o continúa con la actual.");

  } catch (error) {
    notify(error.message, "danger");

  } finally {
    busy = false;
    updateButtons();
  }
}


async function perform(action, extra = {}) {
  if (busy) {
    return;
  }

  busy = true;
  updateButtons();

  try {
    const response = await fetch("/api/cola", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken
      },
      body: JSON.stringify({
        action,
        ...extra
      })
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "No se pudo completar la operación.");
    }

    if (action === "enqueue" || action === "reset") {
      clearPreview();
    }

    if (action === "reset") {
      stopCamera();
    }

    render(result.state);
    notify(result.message, "success");

    if (action === "front") {
      $("#front-card")?.scrollIntoView({
        behavior: "smooth",
        block: "center"
      });
    }

  } catch (error) {
    notify(error.message, "danger");

  } finally {
    busy = false;
    updateButtons();
  }
}


function stopCamera() {
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }

  video.srcObject = null;

  $("#start-camera").disabled = false;
  $("#stop-camera").disabled = true;

  $("#camera-message").textContent = "Cámara apagada.";

  updateButtons();
}


async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    notify(
      "La cámara requiere localhost, 127.0.0.1 o HTTPS.",
      "warning"
    );
    return;
  }

  $("#start-camera").disabled = true;

  $("#camera-message").textContent =
    "Solicitando permiso para usar la cámara…";

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "user",
        width: { ideal: 640 },
        height: { ideal: 480 }
      },
      audio: false
    });

    video.srcObject = stream;
    await video.play();

    $("#stop-camera").disabled = false;
    $("#camera-message").textContent = "Cámara lista.";

    updateButtons();

  } catch (error) {
    stopCamera();

    const messages = {
      NotAllowedError:
        "Permite el acceso a la cámara en el navegador y en Windows.",
      NotFoundError:
        "No se encontró una cámara conectada.",
      NotReadableError:
        "No se pudo abrir la cámara. Comprueba si otra aplicación la utiliza."
    };

    notify(
      messages[error.name] || "No se pudo iniciar la cámara.",
      "danger"
    );
  }
}


function prepareImage(source, width, height) {
  const scale = Math.min(640 / width, 640 / height, 1);

  canvas.width = Math.max(1, Math.round(width * scale));
  canvas.height = Math.max(1, Math.round(height * scale));

  const context = canvas.getContext("2d");

  if (!context) {
    throw new Error("El navegador no pudo preparar la imagen.");
  }

  // Fondo blanco para imágenes con transparencia.
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvas.width, canvas.height);

  context.drawImage(
    source,
    0,
    0,
    canvas.width,
    canvas.height
  );

  preparedPhoto = canvas.toDataURL("image/jpeg", 0.85);

  $("#preview").src = preparedPhoto;
  $("#preview-box").hidden = false;

  updateButtons();
}


function clearPreview() {
  preparedPhoto = "";

  $("#preview").removeAttribute("src");
  $("#preview-box").hidden = true;
  $("#upload").value = "";

  updateButtons();
}


async function capturePhoto() {
  if (!stream || capturing) {
    return;
  }

  capturing = true;
  updateButtons();

  try {
    const delay = Number($("#delay").value);

    for (let remaining = delay; remaining > 0; remaining--) {
      if (!stream) {
        throw new Error("Captura cancelada: la cámara está apagada.");
      }

      $("#camera-message").textContent =
        `Sonríe… ${remaining}`;

      await new Promise((resolve) => setTimeout(resolve, 1000));
    }

    if (!stream || !video.videoWidth || !video.videoHeight) {
      throw new Error("La cámara todavía no tiene una imagen disponible.");
    }

    prepareImage(
      video,
      video.videoWidth,
      video.videoHeight
    );

    $("#camera-message").textContent = "Fotografía tomada.";

    notify(
      "Revisa la vista previa y pulsa Agregar al final de la cola."
    );

  } catch (error) {
    notify(error.message, "warning");

  } finally {
    capturing = false;
    updateButtons();
  }
}


async function uploadPhoto(event) {
  const file = event.target.files[0];

  if (!file) {
    return;
  }

  const allowed = ["image/jpeg", "image/png", "image/webp"];

  if (!allowed.includes(file.type)) {
    notify("Selecciona una imagen JPEG, PNG o WebP.", "warning");
    event.target.value = "";
    return;
  }

  if (file.size > 5 * 1024 * 1024) {
    notify("La imagen no debe superar 5 MB.", "warning");
    event.target.value = "";
    return;
  }

  loadingImage = true;
  updateButtons();

  const objectUrl = URL.createObjectURL(file);

  try {
    const image = new Image();
    image.src = objectUrl;

    await image.decode();

    if (!image.naturalWidth || !image.naturalHeight) {
      throw new Error("La imagen no tiene dimensiones válidas.");
    }

    prepareImage(
      image,
      image.naturalWidth,
      image.naturalHeight
    );

    notify("Imagen preparada. Ya puedes agregarla a la cola.");

  } catch (error) {
    notify("No se pudo abrir la imagen seleccionada.", "danger");

  } finally {
    URL.revokeObjectURL(objectUrl);
    loadingImage = false;
    event.target.value = "";
    updateButtons();
  }
}


$("#create-form").addEventListener("submit", (event) => {
  event.preventDefault();

  perform("create", {
    capacity: Number($("#capacity").value)
  });
});

$("#start-camera").addEventListener("click", startCamera);
$("#stop-camera").addEventListener("click", stopCamera);
$("#capture").addEventListener("click", capturePhoto);

$("#upload").addEventListener("change", uploadPhoto);
$("#discard").addEventListener("click", clearPreview);

$("#enqueue").addEventListener("click", () => {
  if (!preparedPhoto) {
    notify("Primero prepara una fotografía.", "warning");
    return;
  }

  perform("enqueue", {
    photo: preparedPhoto
  });
});

$("#dequeue").addEventListener("click", () => {
  perform("dequeue");
});

$("#front").addEventListener("click", () => {
  perform("front");
});

$("#reset").addEventListener("click", () => {
  const confirmed = window.confirm(
    "Se eliminarán las fotografías de la cola y la última atendida. ¿Continuar?"
  );

  if (confirmed) {
    perform("reset");
  }
});

window.addEventListener("pagehide", stopCamera);

loadState();