# -*- coding: utf-8 -*-

import asyncio
import io
import traceback
import webbrowser

import mss
import pyaudio

from PIL import Image
from google import genai
from google.genai import types


# =========================================================
# CONFIGURACIÓN
# =========================================================

MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

FORMAT = pyaudio.paInt16
CHANNELS = 1

SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000

# 40 ms
CHUNK_SIZE = 640

SCREEN_INTERVAL = 3.0


# =========================================================
# CLIENTE
# =========================================================

client = genai.Client(
    http_options={
        "api_version": "v1alpha"
    }
)


# =========================================================
# XIMENA
# =========================================================

SYSTEM_INSTRUCTION = """
Eres Ximena, la asistente personal de Vicente.

Tu nombre es Ximena.
Nunca digas que eres Gemini.
Nunca te presentes como Gemini.

Habla siempre en español de España.

Sé natural, cercana, inteligente, espontánea y rápida.

Responde en cuanto tengas suficiente información.
Para preguntas sencillas, responde breve y directamente.

No repitas innecesariamente lo que acaba de decir Vicente.
No hagas introducciones innecesarias.
No termines la conversación por tu cuenta.

Tienes acceso a capturas de pantalla periódicas.
Si Vicente pregunta qué ve en pantalla o necesita ayuda
con algo visible, analiza la captura más reciente.

Si Vicente empieza a hablar mientras estás respondiendo,
debes dejar de hablar y escucharle.

Si Vicente te pide abrir YouTube, abrir la página de YouTube
o poner YouTube, utiliza la herramienta abrir_youtube.
No le digas simplemente cómo abrirlo: ejecútalo tú.
"""


# =========================================================
# HERRAMIENTAS
# =========================================================

TOOLS = [
    types.Tool(
        function_declarations=[
            {
                "name": "abrir_youtube",
                "description": (
                    "Abre YouTube en el navegador predeterminado del ordenador. "
                    "Úsala cuando Vicente diga que quiere abrir YouTube, "
                    "abrir la página de YouTube o poner YouTube."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {},
                },
            }
        ]
    )
]


# =========================================================
# CONFIGURACIÓN LIVE
# =========================================================

CONFIG = types.LiveConnectConfig(

    response_modalities=[
        "AUDIO"
    ],

    tools=TOOLS,

    system_instruction=types.Content(
        parts=[
            types.Part(
                text=SYSTEM_INSTRUCTION
            )
        ]
    ),

    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name="Zephyr"
            )
        )
    ),

    input_audio_transcription=(
        types.AudioTranscriptionConfig()
    ),

    output_audio_transcription=(
        types.AudioTranscriptionConfig()
    ),

    context_window_compression=(
        types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow()
        )
    ),

    # VAD rápida
    realtime_input_config=(
        types.RealtimeInputConfig(
            automatic_activity_detection=(
                types.AutomaticActivityDetection(
                    disabled=False,

                    start_of_speech_sensitivity=(
                        types.StartSensitivity
                        .START_SENSITIVITY_HIGH
                    ),

                    end_of_speech_sensitivity=(
                        types.EndSensitivity
                        .END_SENSITIVITY_LOW
                    ),

                    prefix_padding_ms=80,

                    silence_duration_ms=350,
                )
            )
        )
    ),
)


# =========================================================
# PANTALLA
# =========================================================

def capturar_pantalla():

    with mss.MSS() as sct:

        monitor = sct.monitors[1]

        screenshot = sct.grab(
            monitor
        )

        imagen = Image.frombytes(
            "RGB",
            screenshot.size,
            screenshot.rgb
        )

        imagen.thumbnail(
            (1280, 1280)
        )

        buffer = io.BytesIO()

        imagen.save(
            buffer,
            format="JPEG",
            quality=50
        )

        return buffer.getvalue()


# =========================================================
# AUDIO
# =========================================================

class AudioLoop:

    def __init__(self):

        self.audio_in_queue = None
        self.out_queue = None
        self.session = None

        self.audio_stream = None
        self.output_stream = None

        self.pya = pyaudio.PyAudio()

    async def listen_audio(self):

        mic_info = (
            self.pya
            .get_default_input_device_info()
        )

        self.audio_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )

        print(
            "Microfono activado",
            flush=True
        )

        while True:

            data = await asyncio.to_thread(
                self.audio_stream.read,
                CHUNK_SIZE,
                exception_on_overflow=False
            )

            await self.out_queue.put(
                types.Blob(
                    data=data,
                    mime_type="audio/pcm;rate=16000"
                )
            )

    async def send_realtime(self):

        while True:

            msg = await self.out_queue.get()

            await self.session.send_realtime_input(
                audio=msg
            )

    async def enviar_pantalla(self):

        print(
            "Pantalla activa: cada 3 segundos",
            flush=True
        )

        while True:

            try:

                imagen = await asyncio.to_thread(
                    capturar_pantalla
                )

                await self.session.send_realtime_input(
                    video=types.Blob(
                        data=imagen,
                        mime_type="image/jpeg"
                    )
                )

            except Exception as e:

                print(
                    "Error pantalla:",
                    type(e).__name__,
                    e,
                    flush=True
                )

            await asyncio.sleep(
                SCREEN_INTERVAL
            )

    async def ejecutar_herramienta(self, tool_call):
        """Ejecuta las herramientas solicitadas por Ximena."""

        function_responses = []

        for call in tool_call.function_calls:
            try:
                if call.name == "abrir_youtube":
                    print(
                        "Ximena: abriendo YouTube...",
                        flush=True
                    )

                    await asyncio.to_thread(
                        webbrowser.open,
                        "https://www.youtube.com"
                    )

                    result = {
                        "status": "success",
                        "message": "YouTube se ha abierto correctamente."
                    }

                else:
                    result = {
                        "status": "error",
                        "message": f"Herramienta desconocida: {call.name}"
                    }

            except Exception as e:
                print(
                    "Error herramienta:",
                    type(e).__name__,
                    e,
                    flush=True
                )

                result = {
                    "status": "error",
                    "message": str(e)
                }

            function_responses.append(
                types.FunctionResponse(
                    name=call.name,
                    id=call.id,
                    response=result
                )
            )

        await self.session.send_tool_response(
            function_responses=function_responses
        )

    async def receive_audio(self):

        print(
            "Recepcion activada",
            flush=True
        )

        while True:

            turn = self.session.receive()

            async for response in turn:

                # -----------------------------------------
                # AUDIO DE XIMENA
                # -----------------------------------------

                if response.data:

                    await self.audio_in_queue.put(
                        response.data
                    )

                # -----------------------------------------
                # TEXTO
                # -----------------------------------------

                if response.text:

                    print(
                        "Ximena:",
                        response.text,
                        flush=True
                    )

                # -----------------------------------------
                # HERRAMIENTAS
                # -----------------------------------------

                if response.tool_call:
                    await self.ejecutar_herramienta(
                        response.tool_call
                    )

                # -----------------------------------------
                # INTERRUPCIÓN
                # -----------------------------------------

                if (
                    response.server_content
                    and response.server_content.interrupted
                ):

                    print(
                        "Ximena interrumpida",
                        flush=True
                    )

                    # Vaciar TODO el audio pendiente.
                    while True:

                        try:

                            self.audio_in_queue.get_nowait()

                        except asyncio.QueueEmpty:

                            break

            # Vuelve a recibir el siguiente turno
            # sin cerrar la sesión.

    async def play_audio(self):

        self.output_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )

        print(
            "Salida de audio activada",
            flush=True
        )

        while True:

            bytestream = (
                await self.audio_in_queue.get()
            )

            await asyncio.to_thread(
                self.output_stream.write,
                bytestream
            )

    async def run(self):

        try:

            async with (
                client.aio.live.connect(
                    model=MODEL,
                    config=CONFIG
                ) as session,

                asyncio.TaskGroup() as tg
            ):

                self.session = session

                # Cola de audio de salida
                self.audio_in_queue = asyncio.Queue()

                # Cola de entrada pequeña
                self.out_queue = asyncio.Queue(
                    maxsize=5
                )

                tg.create_task(
                    self.send_realtime()
                )

                tg.create_task(
                    self.listen_audio()
                )

                tg.create_task(
                    self.receive_audio()
                )

                tg.create_task(
                    self.play_audio()
                )

                tg.create_task(
                    self.enviar_pantalla()
                )

        except asyncio.CancelledError:

            pass

        except Exception as e:

            print(
                "ERROR:",
                type(e).__name__,
                e,
                flush=True
            )

            traceback.print_exc()

        finally:

            self.close()

    def close(self):

        try:

            if self.audio_stream:

                self.audio_stream.stop_stream()
                self.audio_stream.close()

        except Exception:
            pass

        try:

            if self.output_stream:

                self.output_stream.stop_stream()
                self.output_stream.close()

        except Exception:
            pass

        try:

            self.pya.terminate()

        except Exception:
            pass


# =========================================================
# INICIO
# =========================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("XIMENA LIVE")
    print("=" * 60)
    print()
    print(
        "Modelo:",
        MODEL
    )
    print(
        "Audio: 40 ms por bloque"
    )
    print(
        "Pantalla: cada 3 segundos"
    )
    print(
        "Interrupciones: ACTIVADAS"
    )
    print(
        "Conectando con Ximena..."
    )
    print()

    audio = AudioLoop()

    try:

        asyncio.run(
            audio.run()
        )

    except KeyboardInterrupt:

        print()
        print(
            "Ximena cerrada."
        )

    except Exception as e:

        print(
            "ERROR GENERAL:",
            type(e).__name__,
            e
        )

        traceback.print_exc()