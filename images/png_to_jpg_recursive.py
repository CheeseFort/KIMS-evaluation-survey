import os
from PIL import Image

def convert_pngs_to_jpg(root_dir):
	for root, dirs, files in os.walk(root_dir):
		for filename in files:
			if filename.lower().endswith(".png"):
				png_path = os.path.join(root, filename)
				jpg_path = os.path.splitext(png_path)[0] + ".jpg"

				try:
					with Image.open(png_path) as img:
						# Convert to RGB (JPEG does not support transparency)
						if img.mode in ("RGBA", "LA", "P"):
							rgba = img.convert("RGBA")
							background = Image.new("RGB", rgba.size, (255, 255, 255))
							background.paste(rgba, mask=rgba.getchannel("A"))
							img = background
						else:
							img = img.convert("RGB")

						img.save(jpg_path, "JPEG", quality=95)

					# Delete original only after successful save
					os.remove(png_path)

					print(f"Converted: {png_path}")

				except Exception as e:
					print(f"Failed: {png_path} - {e}")


if __name__ == "__main__":
	directory = input("Enter directory to process: ").strip('" ')
	convert_pngs_to_jpg(directory)
	print("Conversion complete.")
