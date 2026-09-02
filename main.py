from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
import hashlib
from PIL import Image
from PIL.ExifTags import TAGS
import io
import os
import numpy as np

app = FastAPI()
os.makedirs("outputs", exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    file_hash = hashlib.sha256(contents).hexdigest()

    trust_score = 100
    reasons = []
    metadata_findings = []

    filename_lower = (file.filename or "").lower()
    is_pdf = filename_lower.endswith(".pdf")

    is_image = False
    ela_result_path = None
    ela_score = None

    if is_pdf:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(contents))
            info = reader.metadata

            producer = str(info.producer) if info and info.producer else None
            creation_date = str(info.creation_date) if info and info.creation_date else None
            mod_date = str(info.modification_date) if info and info.modification_date else None

            suspicious_pdf_tools = ["photoshop", "gimp", "canva", "ilovepdf", "smallpdf"]

            if producer:
                metadata_findings.append(f"PDF Producer: '{producer}'")
                if any(s in producer.lower() for s in suspicious_pdf_tools):
                    trust_score -= 25
                    reasons.append(f"-25: PDF producer suggests editing/conversion tool ('{producer}').")
            else:
                metadata_findings.append("No producer metadata found in PDF.")
                trust_score -= 10
                reasons.append("-10: No producer metadata present in PDF.")

            if creation_date and mod_date and creation_date != mod_date:
                trust_score -= 20
                reasons.append(f"-20: PDF modification date differs from creation date (created: {creation_date}, modified: {mod_date}) — file was edited after creation.")
            elif creation_date:
                metadata_findings.append(f"Creation date: {creation_date}")

            metadata_findings.append(f"Total pages: {len(reader.pages)}")

        except Exception as e:
            metadata_findings.append(f"Could not read PDF metadata: {str(e)}")

    else:
        suspicious_software = ["photoshop", "gimp", "snapseed", "lightroom", "picsart"]
        try:
            image = Image.open(io.BytesIO(contents))
            is_image = True
            exif_data = image._getexif()

            if exif_data is None:
                metadata_findings.append("No metadata found.")
                trust_score -= 10
                reasons.append("-10: No metadata present (could mean stripped/edited, or just a normal screenshot).")
            else:
                found_software = None
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    if tag_name == "Software":
                        found_software = str(value)

                if found_software:
                    metadata_findings.append(f"Software tag found: '{found_software}'")
                    if any(s in found_software.lower() for s in suspicious_software):
                        trust_score -= 30
                        reasons.append(f"-30: Editing software detected in metadata ('{found_software}').")
                else:
                    metadata_findings.append("No 'Software' tag found.")

        except Exception:
            is_image = False
            metadata_findings.append("Could not read as an image or PDF — unsupported format.")

        if is_image:
            try:
                original = Image.open(io.BytesIO(contents)).convert("RGB")
                resaved_bytes_io = io.BytesIO()
                original.save(resaved_bytes_io, "JPEG", quality=90)
                resaved_bytes_io.seek(0)
                resaved = Image.open(resaved_bytes_io)

                original_np = np.array(original).astype(int)
                resaved_np = np.array(resaved).astype(int)
                diff = np.abs(original_np - resaved_np)
                diff_amplified = np.clip(diff * 15, 0, 255).astype(np.uint8)
                ela_image = Image.fromarray(diff_amplified)

                output_filename = f"ela_{file_hash[:10]}.png"
                output_path = os.path.join("outputs", output_filename)
                ela_image.save(output_path)
                ela_result_path = f"/result-image/{output_filename}"

                ela_score = float(np.mean(diff_amplified))
                grayscale_diff = np.mean(diff_amplified, axis=2)
                max_brightness = float(np.max(grayscale_diff))
                bright_pixel_ratio = float(np.mean(grayscale_diff > 100))

                if ela_score > 20:
                    trust_score -= 25
                    reasons.append(f"-25: High overall ELA variation ({ela_score:.1f}) — possible widespread editing.")
                elif ela_score > 10:
                    trust_score -= 10
                    reasons.append(f"-10: Moderate overall ELA variation ({ela_score:.1f}).")

                if bright_pixel_ratio > 0.001 and bright_pixel_ratio < 0.05:
                    trust_score -= 20
                    reasons.append(f"-20: Localized bright hotspot detected (max intensity {max_brightness:.0f}) — a small region shows much higher compression variation than the rest of the image, consistent with a targeted edit.")

                # --- OCR-based text tampering check ---
                try:
                    import pytesseract
                    from pytesseract import Output

                    default_win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                    if os.path.exists(default_win_path):
                        pytesseract.pytesseract.tesseract_cmd = default_win_path

                    ocr_data = pytesseract.image_to_data(original, output_type=Output.DICT)
                    global_mean = float(np.mean(grayscale_diff))
                    flagged_words = []
                    extracted_words = []

                    n_boxes = len(ocr_data['text'])
                    for i in range(n_boxes):
                        word = ocr_data['text'][i].strip()
                        try:
                            conf = int(ocr_data['conf'][i])
                        except (ValueError, TypeError):
                            conf = -1
                        if word and conf > 40:
                            extracted_words.append(word)
                            x, y, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
                            y2 = min(y + h, grayscale_diff.shape[0])
                            x2 = min(x + w, grayscale_diff.shape[1])
                            if y2 > y and x2 > x:
                                region = grayscale_diff[y:y2, x:x2]
                                region_mean = float(np.mean(region))
                                if region_mean > max(global_mean * 2.5, 60):
                                    flagged_words.append((word, region_mean))

                    if extracted_words:
                        metadata_findings.append(f"OCR detected {len(extracted_words)} text element(s) in image.")
                    else:
                        metadata_findings.append("OCR found no readable text in image.")

                    if flagged_words:
                        trust_score -= 20
                        top_flagged = ", ".join([f"'{w}'" for w, _ in flagged_words[:3]])
                        reasons.append(f"-20: Text region(s) with unusually high compression variation detected near: {top_flagged} — possible localized text edit (e.g. an altered amount, date, or name).")

                except Exception:
                    metadata_findings.append("OCR text-tampering check unavailable (Tesseract OCR engine not found).")

            except Exception as e:
                metadata_findings.append(f"ELA could not be performed: {str(e)}")

    trust_score = max(0, min(100, trust_score))

    if trust_score >= 80:
        verdict = "Likely Authentic"
    elif trust_score >= 50:
        verdict = "Some Concerns — Review Recommended"
    else:
        verdict = "High Risk — Likely Tampered"

    return {
        "filename": file.filename,
        "file_type": "PDF" if is_pdf else ("Image" if is_image else "Unknown"),
        "size_bytes": len(contents),
        "sha256_hash": file_hash,
        "metadata_findings": metadata_findings,
        "ela_score": ela_score,
        "ela_image_url": ela_result_path,
        "trust_score": trust_score,
        "verdict": verdict,
        "score_breakdown": reasons if reasons else ["No issues found — full score."]
    }


@app.post("/compare")
async def compare_files(file_a: UploadFile = File(...), file_b: UploadFile = File(...)):
    contents_a = await file_a.read()
    contents_b = await file_b.read()

    hash_a = hashlib.sha256(contents_a).hexdigest()
    hash_b = hashlib.sha256(contents_b).hexdigest()

    identical = (hash_a == hash_b)

    result = {
        "filename_a": file_a.filename,
        "filename_b": file_b.filename,
        "hash_a": hash_a,
        "hash_b": hash_b,
        "identical": identical,
        "diff_image_url": None,
        "diff_score": None,
        "note": None
    }

    if identical:
        result["note"] = "These files are byte-for-byte identical. No changes detected."
        return result

    try:
        img_a = Image.open(io.BytesIO(contents_a)).convert("RGB")
        img_b = Image.open(io.BytesIO(contents_b)).convert("RGB")

        # Resize B to match A's dimensions so we can compare pixel-by-pixel
        if img_a.size != img_b.size:
            img_b = img_b.resize(img_a.size)

        np_a = np.array(img_a).astype(int)
        np_b = np.array(img_b).astype(int)

        diff = np.abs(np_a - np_b)
        diff_amplified = np.clip(diff * 4, 0, 255).astype(np.uint8)
        diff_image = Image.fromarray(diff_amplified)

        output_filename = f"compare_{hash_a[:8]}_{hash_b[:8]}.png"
        output_path = os.path.join("outputs", output_filename)
        diff_image.save(output_path)

        diff_score = float(np.mean(diff_amplified))
        grayscale_diff = np.mean(diff_amplified, axis=2)
        changed_ratio = float(np.mean(grayscale_diff > 30))

        result["diff_image_url"] = f"/result-image/{output_filename}"
        result["diff_score"] = diff_score
        percent = round(changed_ratio * 100, 2)
        result["changed_area_percent"] = percent

        if percent == 0:
            result["note"] = "Files differ at the byte level, but no visually significant differences were detected — likely a re-save or compression change only."
        elif percent < 2:
            result["note"] = f"A small, concentrated change was found, affecting only {percent}% of the image area. Concentrated edits like this are often more significant than widespread ones — a highly localized change usually means a deliberate, targeted edit rather than a general re-save. Review the highlighted region below."
        elif percent < 15:
            result["note"] = f"A moderate difference was found — {percent}% of the image area shows visible changes. This could indicate a deliberate edit or a substantial re-processing of the file."
        else:
            result["note"] = f"A large difference was found — {percent}% of the image area shows visible changes, suggesting the files may not depict the same scene, or extensive editing has occurred."

    except Exception as e:
        result["note"] = f"Files differ (hashes do not match), but a visual comparison could not be generated: {str(e)}"

    return result


@app.get("/result-image/{filename}")
def get_result_image(filename: str):
    path = os.path.join("outputs", filename)
    return FileResponse(path)
