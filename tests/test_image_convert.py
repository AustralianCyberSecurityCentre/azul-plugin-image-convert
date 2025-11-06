import os
from io import BytesIO

from azul_runner import FV, Event, EventData, JobResult, State, test_template
from PIL import Image

from azul_plugin_image_convert.main import AzulPluginImageConvert


class TestExecute(test_template.TestPlugin):
    PLUGIN_TO_TEST = AzulPluginImageConvert

    @staticmethod
    def current_directory():
        return os.path.split(os.path.realpath(__file__))[0]

    def getOutputImageBytes(self, result: JobResult) -> BytesIO:
        outputHash = None
        for data in result.events[0].data:
            if data.label == "safe_png":
                outputHash = data.hash
        self.assertIsNotNone(outputHash)
        return result.data[outputHash]

    def test_jpg_metadata(self):
        result = self.do_execution(
            data_in=[("content", self.load_local_raw("azul.jpg", description="glitched azul logo jpg."))]
        )

        img = Image.open(self.getOutputImageBytes(result))
        img.load()
        self.assertEqual(len(img.getexif()), 0)

        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        sha256="7f2f1546ecf629ba0f71fd6c3711bf7c15a9d1f845b85512c18433ffc84eed2c",
                        data=[
                            EventData(
                                hash="d25ab8d018f638b097df1a8d75b5cb444ca460d441c3de99f523d96fa8446edb",
                                label="safe_png",
                            )
                        ],
                        features={"image_convert_tool": [FV("pillow")]},
                    )
                ],
                data={"d25ab8d018f638b097df1a8d75b5cb444ca460d441c3de99f523d96fa8446edb": b""},
            ),
        )

    def test_gif_large_transparent(self):
        result = self.do_execution(
            data_in=[("content", self.load_local_raw("cube.gif", description="gif of a 3d rotation cube."))]
        )

        img = Image.open(self.getOutputImageBytes(result))
        self.assertLessEqual(img.height, 512)
        self.assertLessEqual(img.width, 512)

        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        sha256="e341549f817148ac13354e79f43f9c0350f6dd0d98d0fe0d8eb6643d8673d59b",
                        data=[
                            EventData(
                                hash="b4bdcf6ae3c8a94f0d9339366c9fc692860cbe8b4d7ea940ddc846f2ca3cffd8",
                                label="safe_png",
                            )
                        ],
                        features={"image_convert_tool": [FV("pillow")]},
                    )
                ],
                data={"b4bdcf6ae3c8a94f0d9339366c9fc692860cbe8b4d7ea940ddc846f2ca3cffd8": b""},
            ),
        )

    def test_broken_image(self):
        result = self.do_execution(
            data_in=[
                (
                    "content",
                    self.load_test_file_bytes(
                        "d4c5ad99b4dad07a684e60110bc71eabe6edb424fa4dd148708ef437072f5942",
                        "Broken image known to have bad encoding.",
                    ),
                )
            ],
        )

        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.OPT_OUT),
            ),
        )

    def test_unrecognized_data_stream(self):
        data = self.load_test_file_bytes(
            "4233907bfcd3733ea418d3d69b269c3be0598042b5262c8f72621f3733896e28",
            "Partial data streams that appears to be an image based on the header but isn't.",
        )
        result = self.do_execution(data_in=[("content", data)])

        self.assertJobResult(
            result,
            JobResult(
                state=State(
                    State.Label.COMPLETED_WITH_ERRORS,
                    message="Image is Malformed and cannot be converted to another format. Reason : unrecognized data stream contents when reading image file",
                ),
                events=[
                    Event(
                        entity_type="binary",
                        entity_id="4233907bfcd3733ea418d3d69b269c3be0598042b5262c8f72621f3733896e28",
                        features={
                            "malformed": [
                                FV(
                                    "Image is Malformed and cannot be converted to another format. Reason : unrecognized data stream contents when reading image file"
                                )
                            ]
                        },
                    )
                ],
            ),
        )

    def test_broken_data_stream(self):
        data = self.load_test_file_bytes(
            "c08dd20adb464df6765055eaf82765524c6734b1a581ed5c65fb1f9f82ce767e",
            "Not an image appears like a broken data stream.",
        )
        result = self.do_execution(data_in=[("content", data)])

        self.assertJobResult(
            result,
            JobResult(
                state=State(
                    State.Label.COMPLETED_WITH_ERRORS,
                    message="Image is Malformed and cannot be converted to another format. Reason : broken data stream when reading image file",
                ),
                events=[
                    Event(
                        entity_type="binary",
                        entity_id="c08dd20adb464df6765055eaf82765524c6734b1a581ed5c65fb1f9f82ce767e",
                        features={
                            "malformed": [
                                FV(
                                    "Image is Malformed and cannot be converted to another format. Reason : broken data stream when reading image file"
                                )
                            ]
                        },
                    )
                ],
            ),
        )

    def test_wrong_mode(self):
        data = self.load_test_file_bytes(
            "52ae01875785458842477fcd2ec35c0982ef2f5da21b04a45c0e364871aa995b",
            "Benign PNG that has the wrong mode and can cause breaks during decoding.",
        )
        result = self.do_execution(data_in=[("content", data)])

        img = Image.open(self.getOutputImageBytes(result))
        self.assertLessEqual(img.height, 4096)
        self.assertLessEqual(img.width, 4096)

        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        sha256="52ae01875785458842477fcd2ec35c0982ef2f5da21b04a45c0e364871aa995b",
                        data=[
                            EventData(
                                hash="562d2d3e10b7cb1cfe3ad50a09c35492e079f99aedcf05b70179838e68c3d154",
                                label="safe_png",
                            )
                        ],
                        features={"image_convert_tool": [FV("pillow")]},
                    )
                ],
                data={"562d2d3e10b7cb1cfe3ad50a09c35492e079f99aedcf05b70179838e68c3d154": b""},
            ),
        )

    def test_cmyk_formatted_jpg(self):
        """CMYK is one of the colouring formats not supported when converting to PNG."""
        data = self.load_test_file_bytes(
            "188ea3c1b62f0d4326cc7ed6fedb15aaea06a92dc41c9e3a97c321580664694d",
            "Benign JPEG which uses the CMYK format which can cause the plugin to fail to decode.",
        )
        result = self.do_execution(data_in=[("content", data)])
        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        sha256="188ea3c1b62f0d4326cc7ed6fedb15aaea06a92dc41c9e3a97c321580664694d",
                        data=[
                            EventData(
                                hash="f21d9ae31382e3d9ff82f745008363cc97100c2f32b91213f46bf600b80ced34",
                                label="safe_png",
                            )
                        ],
                        features={"image_convert_tool": [FV("pillow")]},
                    )
                ],
                data={"f21d9ae31382e3d9ff82f745008363cc97100c2f32b91213f46bf600b80ced34": b""},
            ),
        )

    def test_oddly_formatted_webp(self):
        """Webp that wouldn't change size like other PNGs due to it's encoding."""
        data = self.load_test_file_bytes(
            "6aeaf5a29af029e018d79b33a37dc53475afc80e9f6458dd07a9dcb624268245",
            "Webp image that wouldn't change size like other PNGs due to it's encoding.",
        )
        result = self.do_execution(data_in=[("content", data)])
        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        sha256="6aeaf5a29af029e018d79b33a37dc53475afc80e9f6458dd07a9dcb624268245",
                        data=[
                            EventData(
                                hash="2cdbae4aaa63d80f9adbd62a95c2c0f1dae4493ec7c0e027f1c7131da52347b2",
                                label="safe_png",
                            )
                        ],
                        features={"image_convert_tool": [FV("pillow")]},
                    )
                ],
                data={"2cdbae4aaa63d80f9adbd62a95c2c0f1dae4493ec7c0e027f1c7131da52347b2": b""},
            ),
        )

    def test_oddly_formatted_png(self):
        """PNG that wouldn't change size like other PNGs due to it's encoding."""
        data = self.load_test_file_bytes(
            "328cd283458670867b954e5df1112165cb562180ac9a26d8c73acd5cc99733ac",
            "Benign PNG that wouldn't change size like other PNGs due to it's encoding.",
        )
        result = self.do_execution(data_in=[("content", data)])
        result.state.message = None
        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        sha256="328cd283458670867b954e5df1112165cb562180ac9a26d8c73acd5cc99733ac",
                        data=[
                            EventData(
                                hash="a0acd5a4daf2d7db7ba67d4b9ebdd0f682266e836c58babc92141addcb6f9fec",
                                label="safe_png",
                            )
                        ],
                        features={"image_convert_tool": [FV("pillow")]},
                    )
                ],
                data={"a0acd5a4daf2d7db7ba67d4b9ebdd0f682266e836c58babc92141addcb6f9fec": b""},
            ),
        )

    def test_opencv_partial_map_data(self):
        """Png that is only partially downloaded and looks clipped that can only be processed by opencv."""
        data = self.load_test_file_bytes(
            "69fcc2691f146e52b0104f0a81e31acec96dc5f428ff375e24778ef49f946848",
            "Benign JPEG that is of a partially downloaded map of europe.",
        )
        result = self.do_execution(data_in=[("content", data)])
        result.state.message = None
        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        sha256="69fcc2691f146e52b0104f0a81e31acec96dc5f428ff375e24778ef49f946848",
                        data=[
                            EventData(
                                hash="d9c42b9e2d43cda09b98d9abc79f58055fdab562084c6846d62688d2d5966f37",
                                label="safe_png",
                            )
                        ],
                        features={
                            "image_convert_tool": [FV("opencv")],
                            "malformed": [
                                FV(
                                    "Image is Malformed and cannot be converted to another format. Reason : image file is truncated (6 bytes not processed)"
                                )
                            ],
                        },
                    )
                ],
                data={"d9c42b9e2d43cda09b98d9abc79f58055fdab562084c6846d62688d2d5966f37": b""},
            ),
        )
