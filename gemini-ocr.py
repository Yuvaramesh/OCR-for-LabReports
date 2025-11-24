import streamlit as st
import google.generativeai as genai
import base64

# -------------------------
# Configure Gemini API
# -------------------------
genai.configure(api_key="AIzaSyBa7FgCwEOU2De-GhwQFACtshXItONeUv8")

model = genai.GenerativeModel("gemini-2.5-flash")


# -------------------------
# Convert image to Base64
# -------------------------
def to_base64(file):
    return base64.b64encode(file.read()).decode()


# -------------------------
# Streamlit UI
# -------------------------
st.title("📄 Image to Text OCR Extractor using Gemini")
st.write(
    "Upload an image and extract all text clearly using Google's Gemini Vision model."
)

uploaded_file = st.file_uploader("Upload an Image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Image", width=350)

    image_base64 = to_base64(uploaded_file)

    if st.button("Extract Text"):
        with st.spinner("Extracting text... please wait ⏳"):
            prompt = "Extract all readable text from this image clearly and accurately."

            response = model.generate_content(
                [prompt, {"mime_type": "image/jpeg", "data": image_base64}]
            )

            extracted_text = response.text

        st.success("✅ Text Extracted Successfully!")
        st.text_area("Extracted Text:", extracted_text, height=300)

        # Download as TXT
        st.download_button(
            label="📥 Download as TXT",
            data=extracted_text,
            file_name="ocr_output.txt",
            mime="text/plain",
        )
