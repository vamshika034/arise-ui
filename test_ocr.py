from PIL import Image, ImageDraw
from src.ocr_reader import OCRReader

image = Image.new("RGB", (600, 250), "white")
draw = ImageDraw.Draw(image)

draw.text((40, 40), "Welcome Back", fill="black")
draw.text((40, 100), "Email Address", fill="black")
draw.text((40, 150), "Login", fill="black")

image.save("ocr_test_image.png")

print("Loading OCR model. The first run may take a few minutes...")
ocr = OCRReader()

results = ocr.extract_text(image)

print("\nRecognized text:")
for item in results:
    print(
        f"Text: {item['text']} | "
        f"Confidence: {item['confidence']:.2f} | "
        f"Box: {item['bbox']}"
    )

print("\nOCR test finished.")