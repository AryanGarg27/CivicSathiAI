
import os
import json
import urllib.request
import urllib.error


class OpenRouterUnavailable(Exception):
    pass


def analyze_photo_openrouter(image_base64, mime_type):
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise OpenRouterUnavailable("OpenRouter API key missing")

    models = [
        "google/gemma-4-26b-a4b-it:free",
        "google/gemma-4-31b-it:free"
    ]

    prompt = (
        "You are analyzing a civic issue photograph. "
        "Describe only what is clearly visible. "
        "Identify potholes, garbage, damaged roads, water "
        "leakage or other visible infrastructure problems. "
        "Do not invent location, dimensions or severity. "
        "If uncertain, clearly state the uncertainty."
    )

    for model in models:
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                f"data:{mime_type};base64,"
                                f"{image_base64}"
                            )
                        }
                    }
                ]
            }],
            "max_tokens": 350
        }

        request = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            print("Trying vision model:", model)

            with urllib.request.urlopen(
                request, timeout=45
            ) as response:
                result = json.load(response)

            content = result["choices"][0]["message"]["content"]

            if isinstance(content, list):
                content = " ".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                )

            if not isinstance(content, str) or not content.strip():
                raise OpenRouterUnavailable(
                    "Empty model response"
                )

            print("Vision analysis successful:", model)

            return {
                "analysis": content.strip(),
                "provider": "openrouter",
                "model": model,
                "advisory_only": True
            }

        except urllib.error.HTTPError as exc:
            print(f"{model} returned HTTP {exc.code}")

            if exc.code in (429, 503):
                continue

            raise OpenRouterUnavailable(
                f"OpenRouter returned HTTP {exc.code}"
            ) from exc

        except (
            urllib.error.URLError,
            TimeoutError
        ) as exc:
            print(f"Network error with {model}: {exc}")
            continue

        except (
            KeyError,
            IndexError,
            ValueError
        ) as exc:
            print(f"Invalid response from {model}: {exc}")
            continue

    raise OpenRouterUnavailable(
        "All configured vision models are unavailable"
    )
