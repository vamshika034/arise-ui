import streamlit as st
import cv2
import numpy as np
from PIL import Image

from src.detector import (
    detect_candidate_regions,
    detect_rectangular_controls,
    draw_regions,
    suggest_component_type,
    remove_duplicate_regions,
)
from src.xml_generator import generate_android_xml
from src.ocr_reader import OCRReader
from src.text_ui_generator import generate_ui_from_description
st.set_page_config(page_title="ARISE-UI • UI Generator", layout="wide")
st.title("ARISE-UI: AI-Powered Android UI Generator")
st.caption("Create Android interfaces from screenshots or text descriptions.")

st.divider()
st.subheader("Choose how you want to create your UI")

mode = st.radio(
    "Select a mode:",
    ["Screenshot to UI", "Text Description to UI"],
    horizontal=True
)

st.divider()
st.warning(
    "The detector proposes regions using OpenCV. Component labels are suggestions and "
    "must be checked by a person; this is not yet a trained semantic detector."
)

if mode == "Screenshot to UI":
    uploaded = st.file_uploader(
        "Upload an Android UI screenshot",
        type=["png", "jpg", "jpeg"]
    )
else:
    st.subheader("Describe the Android interface you want to create")

    description = st.text_area(
        "UI requirements",
        placeholder="Example: Create a shopping app with a search bar, product cards, prices, and Add to Cart buttons.",
        height=150
    )

    st.info(
        "This mode uses predefined rules to generate Android XML. "
        "It does not yet use a trained text-to-UI model."
    )

    if st.button(
        "Generate UI from Description",
        type="primary",
        key="generate_from_description",
        disabled=not description.strip()
    ):
        try:
            generated_xml = generate_ui_from_description(description)

            st.success("Android XML generated successfully!")

            st.subheader("Generated Android XML")
            st.code(generated_xml, language="xml")

            st.download_button(
                "Download Android XML",
                data=generated_xml,
                file_name="activity_text_generated.xml",
                mime="application/xml"
            )

        except Exception as exc:
            st.error(f"Could not generate the UI: {exc}")

    uploaded = None
if uploaded:
    try:
        pil_img = Image.open(uploaded).convert("RGB")
        image = np.array(pil_img)
    except Exception as exc:
        st.error(f"Could not read this image: {exc}")
        st.stop()

    h, w = image.shape[:2]
    st.write(f"Screenshot dimensions: **{w} × {h} px**")
    # Step 2: Automatically recognize text in the screenshot
    st.subheader("Automatic Text Recognition (OCR)")

    if "ocr_results" not in st.session_state:
        st.session_state["ocr_results"] = {}

    ocr_key = f"{uploaded.name}_{uploaded.size}_{w}_{h}"

    if ocr_key not in st.session_state["ocr_results"]:
        with st.spinner("Recognizing text... This may take a minute on the first run."):
            try:
                ocr_reader = OCRReader()
                recognized_text = ocr_reader.extract_text(image)
                st.session_state["ocr_results"][ocr_key] = recognized_text
            except Exception as exc:
                st.error(f"OCR could not process this screenshot: {exc}")
                st.session_state["ocr_results"][ocr_key] = []

    ocr_results = st.session_state["ocr_results"][ocr_key]

    if ocr_results:
        st.success(f"Recognized {len(ocr_results)} text elements.")

        for item in ocr_results:
            st.write(
                f"**Text:** {item['text']}  |  "
                f"**Confidence:** {item['confidence']:.0%}  |  "
                f"**Position:** {item['bbox']}"
            )
    else:
        st.info("No text was recognized in this screenshot.")
        min_area = st.slider("Minimum candidate region area (pixels)", 100, 10000, 700, 100)

    regions = detect_candidate_regions(image, min_area=min_area)
    extra_regions = detect_rectangular_controls(image)
    regions.extend(extra_regions)
    regions = remove_duplicate_regions(regions)

    if not regions:
        st.warning("No regions were detected. Try lowering the minimum area.")
        st.image(image, caption="Original screenshot", use_container_width=True)
        st.stop()

    # Add editable metadata to each region. Keep state stable for this upload.
    upload_key = f"{uploaded.name}_{uploaded.size}_{w}_{h}_{min_area}"
    if st.session_state.get("region_key") != upload_key:
        st.session_state["region_key"] = upload_key
        st.session_state["region_labels"] = [
            {
                "component": suggest_component_type(region, ocr_results),
                "text": next(
                    (
                        item["text"]
                        for item in ocr_results
                        if len(item.get("bbox", [])) == 4
                        and item["bbox"][2] >= region["x"] - 8
                        and item["bbox"][0] <= region["x"] + region["width"] + 8
                        and item["bbox"][3] >= region["y"] - 8
                        and item["bbox"][1] <= region["y"] + region["height"] + 8
                    ),
                    ""
                )
            }
            for region in regions
        ]
    labels = st.session_state["region_labels"]
    st.subheader("1. Inspect detected regions")
    annotated = draw_regions(image, regions)
    left, right = st.columns(2)
    with left:
        st.image(image, caption="Original screenshot", use_container_width=True)
    with right:
        st.image(annotated, caption=f"Detected candidate regions: {len(regions)}", use_container_width=True)

    st.subheader("2. Label components")
    st.write(
        "For each detected region, choose the closest UI component. If a box is not useful, "
        "label it as **Ignore**. Add visible text when you can read it."
    )
    component_types = ["Container", "Text", "Button", "Text input", "Image/Icon", "Checkbox", "Ignore"]
    with st.form("component_labels_form"):
        updated = []
        for i, region in enumerate(regions):
            with st.expander(
                f"Region {i+1} — x:{region['x']}, y:{region['y']}, "
                f"w:{region['width']}, h:{region['height']}",
                expanded=(i < 3)
            ):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(
                        image[region["y"]:region["y"]+region["height"],
                              region["x"]:region["x"]+region["width"]],
                        caption=f"Region {i+1} crop",
                        use_container_width=True
                    )
                with col2:
                    old = labels[i] if i < len(labels) else {"component": "Container", "text": ""}
                    component = st.selectbox(
                        "Component type",
                        component_types,
                        index=component_types.index(old["component"]) if old["component"] in component_types else 0,
                        key=f"component_{upload_key}_{i}"
                    )
                    text_value = st.text_input(
                        "Visible text (optional)",
                        value=old.get("text", ""),
                        key=f"text_{upload_key}_{i}",
                        placeholder="e.g. Humanize AI"
                    )
                updated.append({"component": component, "text": text_value})
        submitted = st.form_submit_button("Save labels and generate XML", type="primary")

    if submitted:
        st.session_state["region_labels"] = updated
        st.session_state["labels_saved_key"] = upload_key

    saved = st.session_state.get("labels_saved_key") == upload_key
    if saved:
        st.success("Labels saved for this screenshot.")
        labels = st.session_state["region_labels"]
        xml = generate_android_xml(regions, labels, w, h)
        st.subheader("3. Generated Android XML")
        st.caption(
            "This is a layout approximation. Pixel-to-dp conversion, nested layout hierarchy, "
            "fonts, colors, and interactions still need to be reconstructed."
        )
        st.code(xml, language="xml")
        st.download_button(
            "Download generated Android XML",
            data=xml,
            file_name="activity_generated.xml",
            mime="application/xml"
        )

        rows = []
        for i, (region, label) in enumerate(zip(regions, labels), start=1):
            if label["component"] == "Ignore":
                continue
            rows.append({
                "id": i,
                "component": label["component"],
                "text": label["text"],
                "x": region["x"],
                "y": region["y"],
                "width": region["width"],
                "height": region["height"],
                "area": region["width"] * region["height"]
            })
        st.subheader("Labelled component summary")
        st.dataframe(rows, use_container_width=True)

        st.download_button(
            "Download component annotations (CSV)",
            data=__import__("pandas").DataFrame(rows).to_csv(index=False).encode("utf-8"),
            file_name="component_annotations.csv",
            mime="text/csv"
        )
else:
    st.markdown("""
    ### Workflow
    1. Upload a screenshot.
    2. Review the candidate boxes.
    3. Assign each useful box a component type and optional visible text.
    4. Generate an XML approximation and export component annotations.
    """)
