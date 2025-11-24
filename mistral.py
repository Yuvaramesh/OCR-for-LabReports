import streamlit as st
import base64
from mistralai import Mistral

# Initialize Mistral Client
client = Mistral(api_key="P2aFfVFz2GDJer1hmMhmWogRk1nscmjK")

st.title("📄 Mistral OCR Extractor")
st.write("Upload a PDF or image and extract text using Mistral OCR.")

uploaded_file = st.file_uploader(
    "Upload PDF or Image", type=["pdf", "png", "jpg", "jpeg"]
)


def ocr_from_local_file(file_bytes, filename):
    """OCR a local file by converting it to a Base64 Data URI."""

    encoded_string = base64.b64encode(file_bytes).decode("utf-8")

    # Detect mime-type and choose proper OCR chunk type
    if filename.lower().endswith(".pdf"):
        mime_type = "application/pdf"
        chunk_type = "document_url"
        key_name = "document_url"

    elif filename.lower().endswith((".jpg", ".jpeg")):
        mime_type = "image/jpeg"
        chunk_type = "image_url"
        key_name = "image_url"

    elif filename.lower().endswith(".png"):
        mime_type = "image/png"
        chunk_type = "image_url"
        key_name = "image_url"

    else:
        raise ValueError("File format not supported.")

    # Create Data URI
    data_uri = f"data:{mime_type};base64,{encoded_string}"

    # Build request dynamically
    document_payload = {"type": chunk_type, key_name: data_uri}

    response = client.ocr.process(
        model="mistral-ocr-latest", document=document_payload, include_image_base64=True
    )
    return response


if uploaded_file:
    st.info("Processing your file... please wait ⏳")

    file_bytes = uploaded_file.read()

    try:
        result = ocr_from_local_file(file_bytes, uploaded_file.name)

        st.success("OCR Extraction Complete! 🎉")

        full_text = ""  # store all pages text

        # Show extracted text page by page
        for idx, page in enumerate(result.pages):
            st.subheader(f"📄 Page {idx + 1}")
            st.markdown(page.markdown)

            full_text += f"\n\n--- Page {idx + 1} ---\n"
            full_text += page.markdown

        # ------------------------------
        # 📥 Download extracted text
        # ------------------------------
        st.download_button(
            label="📥 Download Extracted Text (.txt)",
            data=full_text,
            file_name="ocr_extracted_text.txt",
            mime="text/plain",
        )

    except Exception as e:
        st.error(f"❌ Error: {e}")
