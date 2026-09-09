#ifndef ET_NATIVE_SIGNAL_GENERATOR_HPP
#define ET_NATIVE_SIGNAL_GENERATOR_HPP

#include <cstddef>
#include <cstdint>

#if defined(_WIN32) && defined(ET_SIGNAL_GENERATOR_EXPORTS)
#define ET_SIGNAL_API __declspec(dllexport)
#else
#define ET_SIGNAL_API
#endif

namespace et::offline {

enum class Waveform : std::uint32_t {
    Tone = 0,
    Fsk = 1,
    Sweep = 2,
    Prbs = 3,
    Sine = 4,
    Square = 5,
    Sawtooth = 6,
    Triangle = 7,
    Chirp = 8,
    Awgn = 9,
    DcOffset = 10,
};

struct ComplexI8 {
    std::int8_t re;
    std::int8_t im;
};

struct SignalGeneratorConfig {
    Waveform waveform{Waveform::Tone};
    std::uint32_t sample_rate_hz{48'000};
    double frequency_hz{1'000.0};
    double sweep_start_hz{-5'000.0};
    double sweep_stop_hz{5'000.0};
    double amplitude{0.7};
    std::uint32_t seed{2026};
    std::uint32_t symbol_rate_hz{1'000};
};

class SignalGenerator {
  public:
    explicit SignalGenerator(const SignalGeneratorConfig& config);

    void reset() noexcept;
    std::size_t generate(ComplexI8* output, std::size_t complex_count);

  private:
    double next_uniform() noexcept;
    std::uint32_t next_random() noexcept;
    ComplexI8 quantize(double re, double im) const noexcept;

    SignalGeneratorConfig config_;
    std::uint32_t random_state_{};
    std::uint64_t generated_samples_{};
    double phase_{};
};

}  // namespace et::offline

extern "C" {

enum EtSignalGeneratorStatusV1 : std::int32_t {
    ET_SIGNAL_GENERATOR_OK = 0,
    ET_SIGNAL_GENERATOR_INVALID_ARGUMENT = 1,
    ET_SIGNAL_GENERATOR_INVALID_CONFIG = 2,
};

struct EtSignalGeneratorConfigV1 {
    std::uint32_t abi_version;
    std::uint32_t waveform;
    std::uint32_t sample_rate_hz;
    std::uint32_t symbol_rate_hz;
    double frequency_hz;
    double sweep_start_hz;
    double sweep_stop_hz;
    double amplitude;
    std::uint32_t seed;
};

ET_SIGNAL_API std::int32_t et_signal_generate_v1(
    const EtSignalGeneratorConfigV1* config,
    std::int8_t* interleaved_iq,
    std::size_t complex_count);

}  // extern "C"

#undef ET_SIGNAL_API

#endif
