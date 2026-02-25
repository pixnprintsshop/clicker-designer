import sys
import os
import cv2
import numpy as np


def run(input_png: str, output_pbm: str) -> None:
    """Process PNG to a single PBM mask (legacy entrypoint)."""
    img = _load_and_preprocess(input_png)
    cv2.imwrite(output_pbm, img)


def run_components(input_png: str, output_dir: str) -> list[str]:
    """
    Process PNG into separate PBM masks — one per connected component.
    Returns list of PBM file paths sorted by component area (largest first).
    """
    mask = _load_and_preprocess(input_png)

    # Invert: we need black shapes as foreground (255) for connectedComponents
    inverted = cv2.bitwise_not(mask)
    num_labels, labels = cv2.connectedComponents(inverted, connectivity=8)

    pbm_paths = []
    for label_id in range(1, num_labels):  # skip background (0)
        component = np.where(labels == label_id, 0, 255).astype(np.uint8)

        # Skip tiny noise components
        black_pixels = np.count_nonzero(component == 0)
        if black_pixels < 50:
            continue

        pbm_path = os.path.join(output_dir, f"component_{label_id}.pbm")
        cv2.imwrite(pbm_path, component)
        pbm_paths.append(pbm_path)

    return pbm_paths


PADDING = 80  # white pixel border so no shape touches the image edge


def _load_and_preprocess(input_png: str) -> np.ndarray:
    img = cv2.imread(input_png, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Failed to load image")
    scale_factor = 3
    img = cv2.resize(
        img, None,
        fx=scale_factor, fy=scale_factor,
        interpolation=cv2.INTER_CUBIC,
    )
    # Add white padding so shapes near the SVG boundary don't touch the image edge.
    # Potrace creates artifacts when paths hit the bitmap border.
    img = cv2.copyMakeBorder(
        img, PADDING, PADDING, PADDING, PADDING,
        borderType=cv2.BORDER_CONSTANT, value=255,
    )
    img = cv2.GaussianBlur(img, (3, 3), 0)
    _, mask = cv2.threshold(img, 60, 255, cv2.THRESH_BINARY)
    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 process_mask.py input.png output.pbm")
        sys.exit(1)
    try:
        run(sys.argv[1], sys.argv[2])
        print("Mask saved:", sys.argv[2])
    except ValueError as e:
        print(e)
        sys.exit(1)
