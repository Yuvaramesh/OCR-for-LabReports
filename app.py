from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image

try:
    import pdf2image

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
try:
    import PyPDF2

    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
import os
import io

app = Flask(__name__)

# Configuration
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
app.config["UPLOAD_FOLDER"] = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "tiff", "bmp", "gif"}

# Create upload folder if it doesn't exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OCR Text Extractor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
            text-align: center;
        }
        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            margin-bottom: 20px;
            transition: all 0.3s;
        }
        .upload-area:hover {
            border-color: #764ba2;
            background: #f8f9ff;
        }
        input[type="file"] {
            display: none;
        }
        .file-label {
            background: #667eea;
            color: white;
            padding: 12px 30px;
            border-radius: 5px;
            cursor: pointer;
            display: inline-block;
            transition: background 0.3s;
        }
        .file-label:hover {
            background: #764ba2;
        }
        .file-name {
            margin-top: 15px;
            color: #666;
            font-style: italic;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 40px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
            transition: background 0.3s;
        }
        button:hover {
            background: #764ba2;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .result {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9ff;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .result h3 {
            color: #333;
            margin-bottom: 15px;
        }
        .result pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            color: #555;
            line-height: 1.6;
        }
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .error {
            color: #d32f2f;
            background: #ffebee;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 OCR Text Extractor</h1>
        <form id="uploadForm" enctype="multipart/form-data">
            <div class="upload-area">
                <label for="file" class="file-label">Choose File</label>
                <input type="file" id="file" name="file" accept=".png,.jpg,.jpeg,.pdf,.tiff,.bmp,.gif">
                <div class="file-name" id="fileName">No file chosen</div>
            </div>
            <button type="submit" id="submitBtn">Extract Text</button>
        </form>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Processing...</p>
        </div>
        
        <div id="result"></div>
    </div>

    <script>
        const fileInput = document.getElementById('file');
        const fileName = document.getElementById('fileName');
        const uploadForm = document.getElementById('uploadForm');
        const loading = document.getElementById('loading');
        const result = document.getElementById('result');
        const submitBtn = document.getElementById('submitBtn');

        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                fileName.textContent = this.files[0].name;
            } else {
                fileName.textContent = 'No file chosen';
            }
        });

        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!fileInput.files.length) {
                result.innerHTML = '<div class="error">Please select a file</div>';
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            loading.style.display = 'block';
            result.innerHTML = '';
            submitBtn.disabled = true;

            try {
                const response = await fetch('/extract', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    result.innerHTML = `
                        <div class="result">
                            <h3>Extracted Text:</h3>
                            <pre>${data.text || 'No text found'}</pre>
                        </div>
                    `;
                } else {
                    result.innerHTML = `<div class="error">${data.error}</div>`;
                }
            } catch (error) {
                result.innerHTML = `<div class="error">Error: ${error.message}</div>`;
            } finally {
                loading.style.display = 'none';
                submitBtn.disabled = false;
            }
        });
    </script>
</body>
</html>
"""


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_image(image_path):
    """Extract text from an image file using Tesseract OCR"""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        raise Exception(f"Error processing image: {str(e)}")


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file using multiple methods"""
    text = ""

    # Method 1: Try PyMuPDF (best option - fast and includes OCR for images)
    if PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc):
                # First try to extract existing text
                page_text = page.get_text()

                # If no text found, perform OCR on the page
                if not page_text.strip():
                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(2, 2)
                    )  # 2x zoom for better OCR
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    page_text = pytesseract.image_to_string(img)

                text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            doc.close()
            return text
        except Exception as e:
            print(f"PyMuPDF failed: {e}")

    # Method 2: Try PyPDF2 for text extraction (no OCR)
    if PYPDF2_AVAILABLE:
        try:
            with open(pdf_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"

            # If we got some text, return it
            if text.strip():
                return text
        except Exception as e:
            print(f"PyPDF2 failed: {e}")

    # Method 3: Try pdf2image + OCR (requires poppler)
    if PDF2IMAGE_AVAILABLE:
        try:
            images = pdf2image.convert_from_path(pdf_path)
            text = ""
            for i, img in enumerate(images):
                page_text = pytesseract.image_to_string(img)
                text += f"\n--- Page {i+1} ---\n{page_text}"
            return text
        except Exception as e:
            print(f"pdf2image failed: {e}")

    # If all methods failed
    raise Exception(
        "Unable to process PDF. Please install one of the following:\n"
        "1. PyMuPDF: pip install PyMuPDF (Recommended)\n"
        "2. PyPDF2: pip install PyPDF2 (for text-based PDFs)\n"
        "3. pdf2image with poppler: pip install pdf2image + install poppler system package"
    )


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/extract", methods=["POST"])
def extract_text():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return (
            jsonify(
                {
                    "error": "Invalid file type. Allowed: PNG, JPG, JPEG, PDF, TIFF, BMP, GIF"
                }
            ),
            400,
        )

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Extract text based on file type
        if filename.lower().endswith(".pdf"):
            text = extract_text_from_pdf(filepath)
        else:
            text = extract_text_from_image(filepath)

        # Clean up uploaded file
        os.remove(filepath)

        return jsonify({"text": text.strip()}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
