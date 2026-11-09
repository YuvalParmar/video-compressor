#pragma once

#include <cstdint>
#include <opencv2/core.hpp>
#include <vector>

namespace semantic_codec {

struct CodecSettings {
    int bandwidth_kbps = 10;
    int roi_quality = 85;
    int background_quality = 18;
    int background_block_size = 12;
    int minimum_roi_bytes = 256;
    int max_queue_frames = 2;
};

struct ProcessResult {
    cv::Mat baseline;
    cv::Mat semantic;
    cv::Mat mask;
    std::size_t baseline_bytes = 0;
    std::size_t semantic_bytes = 0;
    std::size_t roi_bytes = 0;
    std::size_t background_bytes = 0;
    bool frame_dropped = false;
};

class CodecEngine {
public:
    explicit CodecEngine(CodecSettings settings = {});
    ProcessResult process(const cv::Mat& frame, const cv::Mat& importance_mask);
    const CodecSettings& settings() const noexcept { return settings_; }

private:
    CodecSettings settings_;
    std::vector<std::uint8_t> encode_jpeg(const cv::Mat& image, int quality) const;
    cv::Mat decode_jpeg(const std::vector<std::uint8_t>& bytes) const;
    cv::Mat degrade_background(const cv::Mat& frame) const;
    std::size_t frame_budget_bytes() const;
};

}  // namespace semantic_codec
