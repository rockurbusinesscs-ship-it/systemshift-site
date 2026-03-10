import base64
import time
from google import genai
from google.genai import types

client = genai.Client(api_key="AIzaSyBckbWXB_2d8wmvYVmWqc1aLqf2SY2T0v0")

OUTPUT_DIR = r"C:\Users\realf\Downloads\systemshift-site\images"

images = [
    {
        "filename": "app-design-hero.png",
        "prompt": "Professional dark UI mockup of a modern business dashboard app displayed on a laptop and phone screen, showing analytics charts, KPIs, and clean data visualization. Deep navy blue and electric blue accent color palette. Sleek, premium tech aesthetic with subtle gradients. No text."
    },
    {
        "filename": "app-design-portal.png",
        "prompt": "Clean modern client portal app interface mockup on a tablet screen, showing appointment booking, messaging inbox, and document sharing features. Warm amber and cream color palette with dark sidebar navigation. Professional SaaS aesthetic. No text."
    },
    {
        "filename": "app-design-mobile.png",
        "prompt": "Three mobile phone screens showing a custom business mobile app with different views: home dashboard, notifications, and booking flow. Rich purple and violet gradient accent colors on dark background. Floating phone mockup style with soft shadows. No text."
    },
    {
        "filename": "app-design-inventory.png",
        "prompt": "Modern inventory management system dashboard on a wide monitor, showing product grid, stock levels, barcode scanner interface, and shipping status. Fresh green and teal color palette on white background. Clean minimalist design. No text."
    },
    {
        "filename": "app-design-ai.png",
        "prompt": "Futuristic AI-powered business app interface on a laptop screen, showing a chat assistant sidebar, automated workflow builder, and smart recommendations panel. Coral orange and warm rose accent colors on dark charcoal background. Premium tech aesthetic. No text."
    },
]

results = {}

for i, img in enumerate(images):
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
                filepath = f"{OUTPUT_DIR}\\{img['filename']}"
                with open(filepath, "wb") as f:
                    f.write(image_data)
                size_kb = len(image_data) / 1024
                print(f"  Saved: {filepath} ({size_kb:.1f} KB)")
                results[img["filename"]] = f"SUCCESS ({size_kb:.1f} KB)"
                saved = True
                break
        if not saved:
            print(f"  WARNING: No image data in response")
            # Print text parts for debugging
            for part in response.candidates[0].content.parts:
                if part.text:
                    print(f"  Text response: {part.text[:200]}")
            results[img["filename"]] = "FAILED - no image data"
    except Exception as e:
        print(f"  ERROR: {e}")
        results[img["filename"]] = f"FAILED - {e}"

    # Small delay between requests to avoid rate limiting
    if i < len(images) - 1:
        time.sleep(2)

print("\n" + "="*50)
print("RESULTS SUMMARY")
print("="*50)
for filename, status in results.items():
    print(f"  {filename}: {status}")
