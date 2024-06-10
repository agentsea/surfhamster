import pytesseract
from PIL import Image, ImageDraw

def merge_results(results):
    prev_elem = None
    elems = []

    for i in range(len(results["text"])):
        x = results["left"][i]
        y = results["top"][i]
        w = results["width"][i]
        h = results["height"][i]
        text = results["text"][i]
        line = results["line_num"][i]

        def start_phrase():
            prev_elem["x"] = x
            prev_elem["y"] = y
            prev_elem["w"] = w
            prev_elem["h"] = h
            prev_elem["text"] = text
            prev_elem["line"] = line

        if prev_elem:
            if line == prev_elem["line"]:
                if prev_elem["x"] + prev_elem["w"] + prev_elem["h"] // 2 >= x:
                    # This word is a part of the phrase, so we redefine the bounding box and text
                    prev_elem["w"] = (x - prev_elem["x"]) + w
                    prev_elem["text"] += " " + text
                else:
                    # This is a new phrase, so we drop the prev into array and start a new one
                    elems.append(prev_elem.copy())
                    start_phrase()
            else:
                # Another line, restart the phrase
                elems.append(prev_elem.copy())
                start_phrase()
        else:
            # We just started, start a phrase
            prev_elem = {
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "text": text,
                "line": line
            }

    elems.append(prev_elem.copy())
    return elems

def find_all_elements(results, text):
    res = []
    for i in results:
        if i["text"].lower().strip() == text.lower().strip():
            res.append(i)
    return res

def draw_bbs(selected_boxes, image_path, output_path):
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    for item in selected_boxes:
        x, y, w, h = item['x'], item['y'], item['w'], item['h']
        draw.rectangle([x, y, x+w, y+h], outline='green', width=2)
    image.save(output_path)
  
def find_boxes_with_text(path, text):
    custom_config = r'--oem 3 --psm 6'
    results = pytesseract.image_to_data(path, 
                                        output_type=pytesseract.Output.DICT, 
                                        config=custom_config)
    merged_results = merge_results(results)
    return find_all_elements(merged_results, text)
