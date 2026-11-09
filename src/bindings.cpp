#include "codec_engine.hpp"

#include <opencv2/core.hpp>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <stdexcept>

namespace py = pybind11;
using semantic_codec::CodecEngine;
using semantic_codec::CodecSettings;

static cv::Mat view_bgr(const py::array_t<std::uint8_t, py::array::c_style>& input) {
    const auto info = input.request();
    if (info.ndim != 3 || info.shape[2] != 3) {
        throw std::invalid_argument("frame must have shape (height, width, 3)");
    }
    return cv::Mat(static_cast<int>(info.shape[0]), static_cast<int>(info.shape[1]),
                   CV_8UC3, info.ptr, static_cast<std::size_t>(info.strides[0]));
}

static cv::Mat view_mask(const py::array_t<std::uint8_t, py::array::c_style>& input) {
    const auto info = input.request();
    if (info.ndim != 2) {
        throw std::invalid_argument("mask must have shape (height, width)");
    }
    return cv::Mat(static_cast<int>(info.shape[0]), static_cast<int>(info.shape[1]),
                   CV_8UC1, info.ptr, static_cast<std::size_t>(info.strides[0]));
}

static py::array copy_image(const cv::Mat& image) {
    py::array_t<std::uint8_t> output({image.rows, image.cols, image.channels()});
    const auto info = output.request();
    cv::Mat destination(image.rows, image.cols, image.type(), info.ptr,
                        static_cast<std::size_t>(info.strides[0]));
    image.copyTo(destination);
    return output;
}

static py::array copy_mask(const cv::Mat& mask) {
    py::array_t<std::uint8_t> output({mask.rows, mask.cols});
    const auto info = output.request();
    cv::Mat destination(mask.rows, mask.cols, mask.type(), info.ptr,
                        static_cast<std::size_t>(info.strides[0]));
    mask.copyTo(destination);
    return output;
}

PYBIND11_MODULE(semantic_codec, module) {
    module.doc() = "Native ROI-aware semantic video codec";
    py::class_<CodecSettings>(module, "CodecSettings")
        .def(py::init<>())
        .def_readwrite("bandwidth_kbps", &CodecSettings::bandwidth_kbps)
        .def_readwrite("roi_quality", &CodecSettings::roi_quality)
        .def_readwrite("background_quality", &CodecSettings::background_quality)
        .def_readwrite("background_block_size", &CodecSettings::background_block_size)
        .def_readwrite("minimum_roi_bytes", &CodecSettings::minimum_roi_bytes)
        .def_readwrite("max_queue_frames", &CodecSettings::max_queue_frames);

    py::class_<CodecEngine>(module, "CodecEngine")
        .def(py::init<CodecSettings>())
        .def("process", [](CodecEngine& engine, py::array_t<std::uint8_t, py::array::c_style> frame,
                           py::array_t<std::uint8_t, py::array::c_style> mask) {
            py::gil_scoped_release release;
            const auto result = engine.process(view_bgr(frame), view_mask(mask));
            py::gil_scoped_acquire acquire;
            py::dict output;
            output["baseline"] = copy_image(result.baseline);
            output["semantic"] = copy_image(result.semantic);
            output["mask"] = copy_mask(result.mask);
            output["baseline_bytes"] = result.baseline_bytes;
            output["semantic_bytes"] = result.semantic_bytes;
            output["roi_bytes"] = result.roi_bytes;
            output["background_bytes"] = result.background_bytes;
            output["frame_dropped"] = result.frame_dropped;
            return output;
        });
}
