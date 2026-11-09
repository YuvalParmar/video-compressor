#include "codec_engine.hpp"

#include <algorithm>
#include <cmath>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>
#include <stdexcept>

namespace semantic_codec {

CodecEngine::CodecEngine(CodecSettings settings) : settings_(settings) {
    if (settings_.bandwidth_kbps <= 0 || settings_.target_fps <= 0 ||
        settings_.roi_bandwidth_percent < 50 || settings_.roi_bandwidth_percent > 100 ||
        settings_.roi_quality < 1 ||
        settings_.roi_quality > 100 || settings_.background_quality < 1 ||
        settings_.background_quality > 100 || settings_.background_block_size < 2) {
        throw std::invalid_argument("invalid codec settings");
    }
}

std::size_t CodecEngine::frame_budget_bytes() const {
    // The demo budget is application-level: kbps divided by the configured FPS.
    return std::max<std::size_t>(1, static_cast<std::size_t>(
        std::floor(settings_.bandwidth_kbps * 1000.0 / 8.0 / settings_.target_fps)));
}

std::size_t CodecEngine::roi_budget_bytes() const {
    return std::max<std::size_t>(
        1, frame_budget_bytes() * static_cast<std::size_t>(settings_.roi_bandwidth_percent) / 100);
}

std::vector<std::uint8_t> CodecEngine::encode_jpeg(const cv::Mat& image, int quality) const {
    std::vector<std::uint8_t> encoded;
    std::vector<int> params{cv::IMWRITE_JPEG_QUALITY, quality,
                            cv::IMWRITE_JPEG_OPTIMIZE, 1};
    if (!cv::imencode(".jpg", image, encoded, params)) {
        throw std::runtime_error("OpenCV failed to encode JPEG");
    }
    return encoded;
}

cv::Mat CodecEngine::decode_jpeg(const std::vector<std::uint8_t>& bytes) const {
    cv::Mat decoded = cv::imdecode(bytes, cv::IMREAD_COLOR);
    if (decoded.empty()) {
        throw std::runtime_error("OpenCV failed to decode JPEG");
    }
    return decoded;
}

cv::Mat CodecEngine::degrade_background(const cv::Mat& frame) const {
    const int block = settings_.background_block_size;
    const cv::Size reduced(std::max(1, frame.cols / block),
                           std::max(1, frame.rows / block));
    cv::Mat small;
    cv::resize(frame, small, reduced, 0, 0, cv::INTER_AREA);
    cv::Mat degraded;
    cv::resize(small, degraded, frame.size(), 0, 0, cv::INTER_NEAREST);
    return degraded;
}

ProcessResult CodecEngine::process(const cv::Mat& frame,
                                   const cv::Mat& importance_mask) {
    if (frame.empty() || frame.type() != CV_8UC3) {
        throw std::invalid_argument("frame must be a non-empty CV_8UC3 image");
    }
    if (importance_mask.empty() || importance_mask.size() != frame.size() ||
        importance_mask.type() != CV_8UC1) {
        throw std::invalid_argument("importance mask must be CV_8UC1 and match frame size");
    }

    ProcessResult result;
    result.mask = importance_mask.clone();
    const std::size_t budget = frame_budget_bytes();

    const auto baseline_bytes = encode_jpeg(frame, settings_.background_quality);
    result.baseline_bytes = baseline_bytes.size();
    result.baseline = decode_jpeg(baseline_bytes);

    cv::Mat softened_mask;
    cv::GaussianBlur(importance_mask, softened_mask, cv::Size(0, 0), 1.5);
    cv::Mat background = degrade_background(frame);
    cv::Mat roi(frame.size(), frame.type(), cv::Scalar::all(0));
    frame.copyTo(roi, importance_mask);
    const auto roi_encoded = encode_jpeg(roi, settings_.roi_quality);
    const auto background_encoded = encode_jpeg(background, settings_.background_quality);

    std::vector<std::uint8_t> selected_roi = roi_encoded;
    std::vector<std::uint8_t> selected_background = background_encoded;
    // Preserve the ROI reservation by repeatedly lowering JPEG quality. JPEG
    // packets are never truncated because truncated packets cannot be decoded.
    const std::size_t roi_budget = std::min(
        frame_budget_bytes(),
        std::max<std::size_t>(
            roi_budget_bytes(), static_cast<std::size_t>(settings_.minimum_roi_bytes)));
    for (int quality = settings_.roi_quality; quality >= 10 &&
         selected_roi.size() > roi_budget; quality -= 10) {
        selected_roi = encode_jpeg(roi, quality);
    }
    const std::size_t background_budget = budget > selected_roi.size()
        ? budget - selected_roi.size() : 1;
    for (int quality = settings_.background_quality; quality >= 5 &&
         selected_background.size() > background_budget; quality -= 5) {
        selected_background = encode_jpeg(background, quality);
    }

    cv::Mat decoded_roi = decode_jpeg(selected_roi);
    cv::Mat decoded_background = decode_jpeg(selected_background);
    cv::Mat semantic = decoded_background.clone();
    decoded_roi.copyTo(semantic, softened_mask);
    result.semantic = semantic;
    result.roi_bytes = selected_roi.size();
    result.background_bytes = selected_background.size();
    result.semantic_bytes = result.roi_bytes + result.background_bytes;
    result.frame_dropped = result.semantic_bytes > budget;
    return result;
}

}  // namespace semantic_codec
