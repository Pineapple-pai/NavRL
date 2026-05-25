import argparse
import os

import cv2
import numpy as np


def resize_to_height(frame, target_height):
    height, width = frame.shape[:2]
    if height == target_height:
        return frame
    scale = target_height / float(height)
    target_width = max(int(width * scale), 1)
    return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)


def add_title(frame, title):
    canvas = frame.copy()
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 48), (0, 0, 0), -1)
    cv2.putText(canvas, title, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    return canvas


def main():
    parser = argparse.ArgumentParser(description="Combine two mp4 demo videos side by side.")
    parser.add_argument("--left", required=True, help="Left input video")
    parser.add_argument("--right", required=True, help="Right input video")
    parser.add_argument("--output", required=True, help="Output mp4 path")
    parser.add_argument("--left-title", default="Before", help="Title for left video")
    parser.add_argument("--right-title", default="After", help="Title for right video")
    args = parser.parse_args()

    left_cap = cv2.VideoCapture(args.left)
    right_cap = cv2.VideoCapture(args.right)

    if not left_cap.isOpened():
        raise RuntimeError(f"Failed to open left video: {args.left}")
    if not right_cap.isOpened():
        raise RuntimeError(f"Failed to open right video: {args.right}")

    fps_left = left_cap.get(cv2.CAP_PROP_FPS) or 20.0
    fps_right = right_cap.get(cv2.CAP_PROP_FPS) or 20.0
    fps = min(fps_left, fps_right)

    width_left = int(left_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height_left = int(left_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    width_right = int(right_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height_right = int(right_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    target_height = min(height_left, height_right)

    sample_left = np.zeros((target_height, width_left, 3), dtype=np.uint8)
    sample_right = np.zeros((target_height, width_right, 3), dtype=np.uint8)
    sample_left = resize_to_height(sample_left, target_height)
    sample_right = resize_to_height(sample_right, target_height)
    combined_width = sample_left.shape[1] + sample_right.shape[1]

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    writer = cv2.VideoWriter(
        args.output,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (combined_width, target_height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Failed to open writer for: {args.output}")

    try:
        while True:
            ok_left, frame_left = left_cap.read()
            ok_right, frame_right = right_cap.read()
            if not ok_left or not ok_right:
                break

            frame_left = resize_to_height(frame_left, target_height)
            frame_right = resize_to_height(frame_right, target_height)
            frame_left = add_title(frame_left, args.left_title)
            frame_right = add_title(frame_right, args.right_title)
            combined = np.concatenate([frame_left, frame_right], axis=1)
            writer.write(combined)
    finally:
        left_cap.release()
        right_cap.release()
        writer.release()

    print(f"Combined video saved to {args.output}")


if __name__ == "__main__":
    main()
