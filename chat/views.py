from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from google import genai
from django.conf import settings

try:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
except AttributeError:
    print("ADVERTENCIA: No se encontró GEMINI_API_KEY en settings.py. Se intentará usar la variable de entorno.")
    client = genai.Client()

MODEL_NAME = "gemini-2.5-flash"

@csrf_exempt
def chat(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "")

            if not user_message:
                return JsonResponse({"error": "El campo 'message' es obligatorio"}, status=400)

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    user_message
                ]
            )

            bot_reply = response.text
            
            return JsonResponse({"reply": bot_reply})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Formato JSON inválido"}, status=400)
        except Exception as e:
            return JsonResponse({"error": f"Error en la API de Gemini: {str(e)}"}, status=500)

    return JsonResponse({"error": "Método no permitido"}, status=405)