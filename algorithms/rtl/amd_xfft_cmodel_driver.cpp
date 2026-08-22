#include "xfft_v9_1_bitacc_cmodel.h"

#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr int kFrameLength = 4096;
constexpr int kOutputWidth = 29;
constexpr double kQ15Scale = 32768.0;

int16_t low_i(uint32_t word) { return static_cast<int16_t>(word & 0xffffU); }
int16_t high_q(uint32_t word) { return static_cast<int16_t>((word >> 16) & 0xffffU); }

std::vector<uint32_t> read_words(const std::string& path) {
  std::ifstream stream(path);
  if (!stream) throw std::runtime_error("cannot open input: " + path);
  std::vector<uint32_t> words;
  std::string line;
  while (std::getline(stream, line)) {
    if (!line.empty()) words.push_back(static_cast<uint32_t>(std::stoul(line, nullptr, 16)));
  }
  return words;
}

int32_t exact_q15_code(double value) {
  const double scaled = value * kQ15Scale;
  const double rounded = std::nearbyint(scaled);
  if (std::abs(scaled - rounded) > 1e-7)
    throw std::runtime_error("C-model output is not integral at the Q15 boundary");
  const auto code = static_cast<int64_t>(rounded);
  const int64_t lower = -(int64_t{1} << (kOutputWidth - 1));
  const int64_t upper = (int64_t{1} << (kOutputWidth - 1)) - 1;
  if (code < lower || code > upper) throw std::runtime_error("C-model output exceeds signed 29 bits");
  return static_cast<int32_t>(code);
}
}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 4) {
      std::cerr << "usage: amd_xfft_cmodel_driver INPUT_MEM OUTPUT_MEM FRAME_COUNT\n";
      return 2;
    }
    const int frame_count = std::stoi(argv[3]);
    const auto words = read_words(argv[1]);
    if (frame_count <= 0 || words.size() != static_cast<size_t>(frame_count * kFrameLength))
      throw std::runtime_error("input length does not match frame count");

    xilinx_ip_xfft_v9_1_generics generics{};
    generics.C_NFFT_MAX = 12;
    generics.C_ARCH = 3;
    generics.C_HAS_NFFT = 0;
    generics.C_USE_FLT_PT = 0;
    generics.C_INPUT_WIDTH = 16;
    generics.C_TWIDDLE_WIDTH = 24;
    generics.C_HAS_SCALING = 0;
    generics.C_HAS_BFP = 0;
    generics.C_HAS_ROUNDING = 1;
    generics.C_NSSR = 1;
    generics.C_SYSTOLICFFT_INV = 0;

    xilinx_ip_xfft_v9_1_state* state = xilinx_ip_xfft_v9_1_create_state(generics);
    if (state == nullptr) throw std::runtime_error("failed to create AMD FFT C-model state");

    std::ofstream output(argv[2], std::ios::binary);
    if (!output) throw std::runtime_error("cannot open output");
    std::vector<double> xn_re(kFrameLength), xn_im(kFrameLength);
    std::vector<double> xk_re(kFrameLength), xk_im(kFrameLength);
    std::vector<int> scaling_schedule(6, 0);

    for (int frame = 0; frame < frame_count; ++frame) {
      for (int index = 0; index < kFrameLength; ++index) {
        const uint32_t word = words[frame * kFrameLength + index];
        xn_re[index] = static_cast<double>(low_i(word)) / kQ15Scale;
        xn_im[index] = static_cast<double>(high_q(word)) / kQ15Scale;
      }
      xilinx_ip_xfft_v9_1_inputs inputs{};
      inputs.nfft = 12;
      inputs.xn_re = xn_re.data();
      inputs.xn_re_size = kFrameLength;
      inputs.xn_im = xn_im.data();
      inputs.xn_im_size = kFrameLength;
      inputs.scaling_sch = scaling_schedule.data();
      inputs.scaling_sch_size = static_cast<int>(scaling_schedule.size());
      inputs.direction = 1;

      xilinx_ip_xfft_v9_1_outputs outputs{};
      outputs.xk_re = xk_re.data();
      outputs.xk_re_size = kFrameLength;
      outputs.xk_im = xk_im.data();
      outputs.xk_im_size = kFrameLength;
      if (xilinx_ip_xfft_v9_1_bitacc_simulate(state, inputs, &outputs) != 0)
        throw std::runtime_error("AMD FFT C-model simulation failed");
      if (outputs.xk_re_size != kFrameLength || outputs.xk_im_size != kFrameLength)
        throw std::runtime_error("AMD FFT C-model returned an unexpected output length");

      for (int index = 0; index < kFrameLength; ++index) {
        const uint32_t real = static_cast<uint32_t>(exact_q15_code(outputs.xk_re[index]));
        const uint32_t imag = static_cast<uint32_t>(exact_q15_code(outputs.xk_im[index]));
        const uint64_t packed = static_cast<uint64_t>(real) | (static_cast<uint64_t>(imag) << 32);
        output << std::hex << std::setfill('0') << std::setw(16) << packed << '\n';
      }
    }
    xilinx_ip_xfft_v9_1_destroy_state(state);
    std::cout << "PHASE-06D C-MODEL PASS: frames=" << frame_count
              << " samples=" << words.size() << '\n';
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "PHASE-06D C-MODEL FAIL: " << error.what() << '\n';
    return 1;
  }
}
