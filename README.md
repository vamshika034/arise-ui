# ARISE-UI Starter Baseline

**Working title:** Adaptive Reconstruction and Iterative Self-Evaluation for Android User Interfaces

This is a starter prototype for the baseline stage. It:
1. accepts a screenshot,
2. applies a lightweight OpenCV heuristic to suggest candidate UI regions,
3. displays candidate bounding boxes,
4. generates illustrative Android XML,
5. computes a basic visual comparison if a reconstructed screenshot is supplied.

## Important limitations
- The OpenCV detector here is a **heuristic baseline**, not a trained UI detector and not a research result.
- Contours are not reliable semantic labels. A rectangle may be a button, card, image, or decoration.
- The XML output is a starting approximation and may need adjustment before it compiles or looks correct.
- Do not claim novelty or improved accuracy until the literature review and controlled evaluation are complete.

## Setup (Windows 11)
Use Python 3.10 or 3.11 if possible. Create a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, use Command Prompt:
```bat
.venv\\Scripts\\activate.bat
```

## GPU note
This first baseline uses OpenCV and does not require the NVIDIA GPU. This is intentional: your system has 8 GB RAM and 4 GB dedicated VRAM, so start with a lightweight pipeline before adding a pretrained detector or fine-tuning.

## Next milestones
1. Replace heuristic region proposals with a trained UI detector.
2. Prepare annotations using RICO screenshots and view hierarchies.
3. Generate more robust XML with constraints and a renderer.
4. Add iterative localized correction.
5. Evaluate on held-out apps (split by app, not random screenshots).
