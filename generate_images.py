import time
import base64
import os
from google import genai
from google.genai import types

client = genai.Client(api_key="AIzaSyBckbWXB_2d8wmvYVmWqc1aLqf2SY2T0v0")

OUTPUT_DIR = r"C:\Users\realf\Downloads\systemshift-site\images"

images = [
    {
        "filename": "cs-financial-advisor.png",
        "prompt": "Professional photograph of a confident African American man in his early 40s wearing a sharp navy suit and tie, standing in a modern financial office with glass walls and city views behind him. Natural lighting from large windows. He's smiling warmly at the camera with his arms crossed. Shallow depth of field. Shot on Canon EOS R5 with 85mm f/1.4 lens. Photojournalistic style. No text."
    },
    {
        "filename": "cs-cole-sms.png",
        "prompt": "Candid professional photograph of a young white man in his late 20s with short brown hair, wearing a casual button-down shirt, sitting at a desk with a laptop and phone visible. Modern startup office environment with exposed brick walls. He's looking at the camera with a confident half-smile. Natural warm window light. Shot on Sony A7III with 50mm f/1.8 lens. Documentary photography style. No text."
    },
    {
        "filename": "cs-logistics.png",
        "prompt": "Professional photograph of a Hispanic woman in her mid-30s wearing a dark polo shirt with a clipboard, standing in a busy warehouse with shelving racks and shipping boxes behind her. Industrial fluorescent and natural light mix. She looks directly at camera with a determined, professional expression. Shot on Nikon Z6 with 35mm lens. Corporate documentary photography style. No text."
    },
    {
        "filename": "cs-esqgo.png",
        "prompt": "Professional photograph of two young Latino men in their late 20s in a modern co-working space, both wearing business casual clothing. One is seated at a laptop, the other standing beside him leaning on the desk. Both looking at camera with confident expressions. Clean modern office with plants and natural light. Shot on Canon 5D Mark IV with 24-70mm f/2.8 lens. Startup team portrait style. No text."
    },
    {
        "filename": "cs-hero-bg.png",
        "prompt": "Wide angle photograph of a modern office meeting room with a large screen showing analytics dashboards and charts. Glass walls, sleek furniture, warm ambient lighting. The room is empty — focus on the environment. Cinematic color grading with warm tones. Shot on Sony A7RV with 16-35mm f/2.8 lens. Architectural photography style. No text."
    },
]

results = []

for i, img in enumerate(images):
    filepath = os.path.join(OUTPUT_DIR, img["filename"])
    print(f"\n[{i+1}/5] Generating {img['filename']}...")
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=img["prompt"],
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )
        saved = False
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_data = base64.b64decode(part.inline_data.data) if isinstance(part.inline_data.data, str) else part.inline_data.data
                with open(filepath, "wb") as f:
                    f.write(image_data)
                size_kb = os.path.getsize(filepath) / 1024
                print(f"  SUCCESS — {size_kb:.1f} KB")
                results.append((img["filename"], True, f"{size_kb:.1f} KB"))
                saved = True
                break
        if not saved:
            print("  FAILED — no image data in response")
            results.append((img["filename"], False, "No image data"))
    except Exception as e:
        print(f"  FAILED — {e}")
        results.append((img["filename"], False, str(e)))

    # Small delay between requests to avoid rate limiting
    if i < len(images) - 1:
        time.sleep(3)

print("\n" + "="*60)
print("RESULTS SUMMARY")
print("="*60)
for filename, success, detail in results:
    status = "OK" if success else "FAIL"
    print(f"  [{status}] {filename} — {detail}")
