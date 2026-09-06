import os
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext


# =========================================================
# CONFIGURACIÓN
# =========================================================

BASE_DIR = r"C:\Users\Vicente"
MOTOR = os.path.join(
    BASE_DIR,
    "google_live.py"
)

PROCESO = None


# =========================================================
# ACTUALIZAR INTERFAZ
# =========================================================

def escribir(texto):
    def actualizar():
        conversacion.insert(
            tk.END,
            texto + "\n"
        )
        conversacion.see(tk.END)

    ventana.after(
        0,
        actualizar
    )


def cambiar_estado(texto):
    ventana.after(
        0,
        lambda: estado.config(
            text=texto
        )
    )


# =========================================================
# LEER SALIDA DEL MOTOR
# =========================================================

def leer_motor():

    global PROCESO

    if PROCESO is None:
        return

    try:

        for linea in iter(
            PROCESO.stdout.readline,
            ""
        ):

            if not linea:
                break

            linea = linea.strip()

            if not linea:
                continue

            escribir(
                linea
            )

            texto = linea.lower()

            if "conectada" in texto:
                cambiar_estado(
                    "🟢 Ximena conectada"
                )

            elif "escuchando" in texto:
                cambiar_estado(
                    "🎤 Escuchando"
                )

            elif "micrófono activado" in texto:
                cambiar_estado(
                    "🎤 Escuchando"
                )

            elif "hablando" in texto:
                cambiar_estado(
                    "🔊 Ximena hablando"
                )

            elif "interrumpida" in texto:
                cambiar_estado(
                    "🎤 Te escucho"
                )

            elif "error" in texto:
                cambiar_estado(
                    "❌ Error"
                )

    except Exception as e:

        escribir(
            "Error leyendo Ximena: "
            + str(e)
        )

    finally:

        cambiar_estado(
            "⏹️ Ximena detenida"
        )


# =========================================================
# ARRANCAR XIMENA
# =========================================================

def arrancar():

    global PROCESO

    if PROCESO is not None:

        if PROCESO.poll() is None:
            return

    try:

        escribir(
            "🚀 Iniciando Ximena..."
        )

        cambiar_estado(
            "🔄 Conectando..."
        )

        creationflags = 0

        if os.name == "nt":

            creationflags = (
                subprocess.CREATE_NO_WINDOW
            )

        PROCESO = subprocess.Popen(

            [
                "python",
                "-u",
                MOTOR
            ],

            cwd=BASE_DIR,

            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,

            stdin=subprocess.DEVNULL,

            text=True,
            encoding="utf-8",
            errors="replace",

            bufsize=1,

            creationflags=creationflags
        )

        threading.Thread(
            target=leer_motor,
            daemon=True
        ).start()

    except Exception as e:

        escribir(
            "❌ No se pudo iniciar Ximena:"
        )

        escribir(
            str(e)
        )

        cambiar_estado(
            "❌ Error"
        )


# =========================================================
# DETENER XIMENA
# =========================================================

def detener():

    global PROCESO

    if PROCESO is None:
        return

    try:

        PROCESO.terminate()

        try:
            PROCESO.wait(
                timeout=3
            )
        except subprocess.TimeoutExpired:
            PROCESO.kill()

    except Exception as e:

        escribir(
            "Error al cerrar: "
            + str(e)
        )

    PROCESO = None

    cambiar_estado(
        "⏹️ Ximena detenida"
    )


# =========================================================
# CERRAR APP
# =========================================================

def cerrar():

    detener()

    ventana.destroy()


# =========================================================
# INTERFAZ
# =========================================================

ventana = tk.Tk()

ventana.title(
    "Ximena - Asistente IA"
)

ventana.geometry(
    "1000x700"
)

ventana.minsize(
    800,
    550
)

ventana.protocol(
    "WM_DELETE_WINDOW",
    cerrar
)

ventana.grid_columnconfigure(
    0,
    weight=1
)

ventana.grid_rowconfigure(
    3,
    weight=1
)


# =========================================================
# TITULO
# =========================================================

titulo = tk.Label(
    ventana,
    text="🤖 XIMENA",
    font=(
        "Arial",
        30,
        "bold"
    )
)

titulo.grid(
    row=0,
    column=0,
    pady=(25, 5)
)


subtitulo = tk.Label(
    ventana,
    text="Asistente personal por voz",
    font=(
        "Arial",
        11
    )
)

subtitulo.grid(
    row=1,
    column=0,
    pady=(0, 10)
)


# =========================================================
# ESTADO
# =========================================================

estado = tk.Label(
    ventana,
    text="⏹️ Ximena detenida",
    font=(
        "Arial",
        13,
        "bold"
    )
)

estado.grid(
    row=2,
    column=0,
    pady=5
)


# =========================================================
# CONVERSACIÓN
# =========================================================

conversacion = scrolledtext.ScrolledText(
    ventana,
    wrap=tk.WORD,
    font=(
        "Arial",
        12
    ),
    padx=15,
    pady=15
)

conversacion.grid(
    row=3,
    column=0,
    sticky="nsew",
    padx=25,
    pady=15
)


# =========================================================
# BOTONES
# =========================================================

zona_botones = tk.Frame(
    ventana
)

zona_botones.grid(
    row=4,
    column=0,
    sticky="ew",
    padx=25,
    pady=(0, 20)
)

zona_botones.grid_columnconfigure(
    0,
    weight=1
)

zona_botones.grid_columnconfigure(
    1,
    weight=1
)


boton_arrancar = tk.Button(
    zona_botones,
    text="▶ INICIAR XIMENA",
    font=(
        "Arial",
        14,
        "bold"
    ),
    height=2,
    command=arrancar
)

boton_arrancar.grid(
    row=0,
    column=0,
    sticky="ew",
    padx=(0, 5)
)


boton_detener = tk.Button(
    zona_botones,
    text="⏹ DETENER",
    font=(
        "Arial",
        14,
        "bold"
    ),
    height=2,
    command=detener
)

boton_detener.grid(
    row=0,
    column=1,
    sticky="ew",
    padx=(5, 0)
)


# =========================================================
# MENSAJE
# =========================================================

ayuda = tk.Label(
    ventana,
    text=(
        "El motor de voz utiliza google_live.py. "
        "La interfaz solo controla y muestra su estado."
    ),
    font=(
        "Arial",
        9
    )
)

ayuda.grid(
    row=5,
    column=0,
    pady=(0, 10)
)


# =========================================================
# ARRANCAR VENTANA
# =========================================================

ventana.mainloop()