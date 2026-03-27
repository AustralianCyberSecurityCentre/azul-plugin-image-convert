"""Safe Image Converter plugin.

This plugin takes potentially malicious images and converts them to a format that is safe to display.
"""

import tempfile
from contextlib import suppress
from io import BytesIO

import cv2
from azul_runner import (
    BinaryPlugin,
    DataLabel,
    Feature,
    FeatureType,
    Job,
    State,
    add_settings,
    cmdline_run,
)
from PIL import Image, ImageSequence, UnidentifiedImageError


class AzulPluginImageConvert(BinaryPlugin):
    """This plugin takes potentially malicious images and converts them to a format that is safe to display."""

    VERSION = "2026.03.27"
    SETTINGS = add_settings(
        filter_data_types={"content": ["image/"]},
        max_dimension=(int, 512),
        animated_data_types=(list[str], ["image/gif", "image/webp"]),
    )
    FEATURES = [
        Feature("image_convert_tool", desc="Image converter used to convert the image.", type=FeatureType.String),
        Feature(
            "image_is_animated",
            desc="True/False value to indicate that the image is an animated (typically gif/webp).",
            type=FeatureType.String,
        ),
        Feature("malformed", desc="Image can be loaded but is malformed in some way.", type=FeatureType.String),
    ]

    def limit_width_and_height(self, original_width: int, original_height: int) -> tuple[int, int]:
        """Calculate the new height and width within the max dimension."""
        if original_height >= original_width and original_height > self.cfg.max_dimension:
            new_height = self.cfg.max_dimension
            aspect = new_height / original_height
            new_width = original_width * aspect
        elif original_width > original_height and original_width > self.cfg.max_dimension:
            new_width = self.cfg.max_dimension
            aspect = new_width / original_width
            new_height = original_height * aspect
        else:
            new_height = original_width
            new_width = original_height

        return int(new_width), int(new_height)

    def try_opencv(self, path: str) -> bool:
        """Try to use opencv to process the image if it succeeds return true."""
        with suppress(Exception):
            # read and resize the image
            image = cv2.imread(path)
            original_width, original_height = image.shape[:2]
            new_width, new_height = self.limit_width_and_height(original_width, original_height)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            original_width, original_height = image.shape[:2]

            with tempfile.NamedTemporaryFile("rb", suffix=".png") as f:
                cv2.imwrite(f.name, image)
                self.add_data_file(DataLabel.SAFE_PNG, {}, f)
            self.add_feature_values("image_convert_tool", "opencv")
            return True
        return False

    def _resize_image(self, img_source: Image.Image, allow_marking_malformed: bool = True) -> Image.Image:
        """Resize the provided image if necessary."""
        biggestDimension = 0
        resize = False
        if img_source.width >= img_source.height and img_source.width > self.cfg.max_dimension:
            resize = True
            biggestDimension = img_source.width
        elif img_source.height > img_source.width and img_source.height > self.cfg.max_dimension:
            resize = True
            biggestDimension = img_source.height

        if resize:
            resizeFactor = 2 * biggestDimension // self.cfg.max_dimension
            try:
                img_source = img_source.reduce(resizeFactor)
            # Catch when the imgSource's mode is invalid
            except ValueError as e:
                description = (
                    "Image is malformed and cannot be resized, continuing with full size image." + f" Reason: {str(e)}"
                )
                self.add_feature_values("malformed", description[: self.cfg.max_value_length - 1])
        return img_source

    def extract_safe_png(self, filepath: str) -> State | None:
        """Attempt to extract the provided image file as a safe png."""
        try:
            img_source = Image.open(filepath)
        except UnidentifiedImageError:
            # Pillow wasn't able to open this file - magic likely doesn't match
            # try alternative library opencv then mark the image as malformed if it fails.
            if self.try_opencv(filepath):
                return
            return State(State.Label.OPT_OUT)
        try:
            img_source = img_source.convert(mode="RGBA")
        except OSError as e:
            description = f"Image is Malformed and cannot be converted to another format. Reason : {str(e)}"
            self.add_feature_values("malformed", description[: self.cfg.max_value_length - 1])
            # try alternative library opencv then mark the image as malformed if it fails.
            if self.try_opencv(filepath):
                return
            return State(State.Label.COMPLETED_WITH_ERRORS, message=description)

        # Attempt to resize the image to save space.
        img_source = self._resize_image(img_source)

        # Convert image to/from bytes to try and remove any malicious content.
        imgResult = Image.frombytes(mode="RGBA", size=(img_source.width, img_source.height), data=img_source.tobytes())
        byte_result = BytesIO()
        imgResult.save(byte_result, format="WEBP")
        byte_result.seek(0)
        self.add_data(DataLabel.SAFE_PNG, {}, byte_result.read())
        self.add_feature_values("image_convert_tool", "pillow")

    def extract_safe_animation(self, filepath: str) -> bool:
        """Extract the provided file and convert it to an animated webp, return false if there is any failures."""
        try:
            img_source = Image.open(filepath)
            frames: list[Image.Image] = []
            durations = []

            for frame in ImageSequence.Iterator(img_source):
                # resize each frame to try and reduce storage size (Don't mark malformed if the resize fails).
                converted_frame = frame.convert("RGBA")
                converted_frame = self._resize_image(converted_frame, allow_marking_malformed=False)
                frames.append(converted_frame)
                durations.append(frame.info.get("duration", 100))

            byte_result = BytesIO()
            frames[0].save(
                byte_result,
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                format="WEBP",
                lossless=False,
            )
            byte_result.seek(0)

            self.add_data(DataLabel.SAFE_PNG, {}, byte_result.read())
            self.add_feature_values("image_convert_tool", "pillow")
            return True
        except Exception:
            return False

    def execute(self, job: Job) -> State | None:
        """Run the plugin."""
        # list of formats pillow supports: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
        # in theory all formats that pillow supports could be supported here.
        # note that pillow only does raster images - a different lib would need to be found for vector images.
        filepath = job.get_data().get_filepath()
        if job.event.entity.file_format in self.cfg.animated_data_types:
            # Attempt to extract the image as an animated image
            if self.extract_safe_animation(filepath) is True:
                self.add_feature_values("image_is_animated", "true")
                return

        return self.extract_safe_png(filepath)


def main():
    """Plugin command-line entrypoint."""
    cmdline_run(plugin=AzulPluginImageConvert)


if __name__ == "__main__":
    main()
