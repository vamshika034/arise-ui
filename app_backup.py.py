import streamlit as st
import cv2
import numpy as np
from PIL import Image
from src.detector import detect_candidate_regions, draw_regions
from src.xml_generator import generate_android_xml

st.set_page_config(page_title="ARISE-UI • Component Labelling", layout="wide")
st.title("ARISE-UI: Android Screenshot Reconstruction")
st.caption("Stage 2 • editable component labels • Android XML approximation")

st.warning(
    "The detector proposes regions using OpenCV. Component labels are suggestions and "
    "must be checked by a person; this is not yet a trained semantic detector."
)

uploaded = st.file_uploader("Upload an Android UI screenshot", type=["png", "jpg", "jpeg"])
if uploaded:
    try:
        pil_img = Image.open(uploaded).convert("RGB")
        image = np.array(pil_img)
    except Exception as exc:
        st.error(f"Could not read this image: {exc}")
        st.stop()

    h, w = image.shape[:2]
    st.write(f"Screenshot dimensions: **{w} × {h} px**")
    min_area = st.slider("Minimum candidate region area (pixels)", 100, 10000, 700, 100)
    regions = detect_candidate_regions(image, min_area=min_area)

    if not regions:
        st.warning("No regions were detected. Try lowering the minimum area.")
        st.image(image, caption="Original screenshot", use_container_width=True)
        st.stop()

    # Add editable metadata to each region. Keep state stable for this upload.
    upload_key = f"{uploaded.name}_{uploaded.size}_{w}_{h}_{min_area}"
    if st.session_state.get("region_key") != upload_key:
        st.session_state["region_key"] = upload_key
        st.session_state["region_labels"] = [
            {"component": "Container", "text": ""}
            for _ in regions
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
