#include "signal_generator.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace {

constexpr double kPi = 3.141592653589793238462643383279502884;
constexpr std::size_t kMaximumSamples = 5'000'000;

static_assert(sizeof(et::offline::ComplexI8) == 2, "ComplexI8 iki bayt olmalıdır");

bool finite(double value) noexcept {
    return std::isfinite(value);
}

void validate(const et::offline::SignalGeneratorConfig& config) {
    const auto waveform = static_cast<std::uint32_t>(config.waveform);
    if (waveform > static_cast<std::uint32_t>(et::offline::Waveform::DcOffset)) {
        throw std::invalid_argument("gecersiz dalga sekli");
    }
    if (config.sample_rate_hz < 8'000 || config.sample_rate_hz > 20'000'000) {
        throw std::invalid_argument("ornekleme hizi sinir disinda");
    }
    if (!finite(config.amplitude) || config.amplitude <= 0.0 || config.amplitude > 0.9) {
        throw std::invalid_argument("genlik (0, 0.9] araliginda olmali");
    }
    const double nyquist = static_cast<double>(config.sample_rate_hz) / 2.0;
    if (!finite(config.frequency_hz) || std::abs(config.frequency_hz) >= nyquist) {
        throw std::invalid_argument("frekans Nyquist siniri disinda");
    }
    if (!finite(config.sweep_start_hz) || !finite(config.sweep_stop_hz) ||
        std::abs(config.sweep_start_hz) >= nyquist || std::abs(config.sweep_stop_hz) >= nyquist ||
        config.sweep_start_hz == config.sweep_stop_hz) {
        throw std::invalid_argument("supurme araligi gecersiz");
    }
    if (config.symbol_rate_hz == 0 || config.symbol_rate_hz > config.sample_rate_hz) {
        throw std::invalid_argument("sembol hizi gecersiz");
    }
}

}  // namespace

namespace et::offline {

SignalGenerator::SignalGenerator(const SignalGeneratorConfig& config) : config_(config) {
    validate(config_);
    reset();
}

void SignalGenerator::reset() noexcept {
    random_state_ = config_.seed == 0 ? 0x6D2B79F5U : config_.seed;
    generated_samples_ = 0;
    phase_ = 0.0;
}

std::uint32_t SignalGenerator::next_random() noexcept {
    std::uint32_t value = random_state_;
    value ^= value << 13U;
    value ^= value >> 17U;
    value ^= value << 5U;
    random_state_ = value == 0 ? 0x6D2B79F5U : value;
    return random_state_;
}

double SignalGenerator::next_uniform() noexcept {
    return (static_cast<double>(next_random()) + 1.0) /
           (static_cast<double>(std::numeric_limits<std::uint32_t>::max()) + 2.0);
}

ComplexI8 SignalGenerator::quantize(double re, double im) const noexcept {
    const double magnitude = std::hypot(re, im);
    if (magnitude > 1.0) {
        re /= magnitude;
        im /= magnitude;
    }
    const auto convert = [this](double value) {
        const double scaled = std::round(std::clamp(value, -1.0, 1.0) * config_.amplitude * 127.0);
        return static_cast<std::int8_t>(std::clamp(scaled, -127.0, 127.0));
    };
    return {convert(re), convert(im)};
}

std::size_t SignalGenerator::generate(ComplexI8* output, std::size_t complex_count) {
    if (output == nullptr || complex_count == 0 || complex_count > kMaximumSamples) {
        throw std::invalid_argument("cikis tamponu gecersiz");
    }

    const double sample_rate = static_cast<double>(config_.sample_rate_hz);
    const double phase_step = 2.0 * kPi * config_.frequency_hz / sample_rate;
    const std::uint64_t samples_per_symbol = std::max<std::uint64_t>(
        1U, config_.sample_rate_hz / config_.symbol_rate_hz);
    std::uint32_t fsk_word = next_random();

    for (std::size_t index = 0; index < complex_count; ++index) {
        const std::uint64_t absolute_index = generated_samples_ + index;
        const double raw_cycle =
            static_cast<double>(absolute_index) * config_.frequency_hz / sample_rate;
        const double cycle = raw_cycle - std::floor(raw_cycle);
        double re = 0.0;
        double im = 0.0;

        switch (config_.waveform) {
            case Waveform::Tone:
                re = std::cos(phase_);
                im = std::sin(phase_);
                phase_ += phase_step;
                break;
            case Waveform::Fsk: {
                if (absolute_index % samples_per_symbol == 0) {
                    fsk_word = next_random();
                }
                const double direction = (fsk_word & 1U) == 0U ? -1.0 : 1.0;
                phase_ += direction * phase_step;
                re = std::cos(phase_);
                im = std::sin(phase_);
                break;
            }
            case Waveform::Sweep:
            case Waveform::Chirp: {
                const double progress = complex_count == 1 ? 0.0 :
                    static_cast<double>(index) / static_cast<double>(complex_count - 1);
                const double frequency = config_.sweep_start_hz +
                    (config_.sweep_stop_hz - config_.sweep_start_hz) * progress;
                phase_ += 2.0 * kPi * frequency / sample_rate;
                re = std::cos(phase_);
                im = std::sin(phase_);
                break;
            }
            case Waveform::Prbs:
                re = (next_random() & 1U) == 0U ? -0.7071067811865476 : 0.7071067811865476;
                im = (next_random() & 1U) == 0U ? -0.7071067811865476 : 0.7071067811865476;
                break;
            case Waveform::Sine:
                re = std::sin(2.0 * kPi * cycle);
                break;
            case Waveform::Square:
                re = cycle < 0.5 ? 1.0 : -1.0;
                break;
            case Waveform::Sawtooth:
                re = 2.0 * cycle - 1.0;
                break;
            case Waveform::Triangle:
                re = 1.0 - 4.0 * std::abs(cycle - 0.5);
                break;
            case Waveform::Awgn: {
                const double u1 = next_uniform();
                const double u2 = next_uniform();
                const double radius = std::sqrt(-2.0 * std::log(u1));
                re = std::clamp(radius * std::cos(2.0 * kPi * u2) / 3.0, -1.0, 1.0);
                im = std::clamp(radius * std::sin(2.0 * kPi * u2) / 3.0, -1.0, 1.0);
                break;
            }
            case Waveform::DcOffset:
                re = 1.0;
                break;
        }

        output[index] = quantize(re, im);
        if (std::abs(phase_) > 2.0 * kPi) {
            phase_ = std::fmod(phase_, 2.0 * kPi);
        }
    }

    generated_samples_ += complex_count;
    return complex_count;
}

}  // namespace et::offline

extern "C" std::int32_t et_signal_generate_v1(
    const EtSignalGeneratorConfigV1* config,
    std::int8_t* interleaved_iq,
    std::size_t complex_count) {
    if (config == nullptr || interleaved_iq == nullptr || complex_count == 0 ||
        complex_count > kMaximumSamples) {
        return ET_SIGNAL_GENERATOR_INVALID_ARGUMENT;
    }
    if (config->abi_version != 1U ||
        config->waveform > static_cast<std::uint32_t>(et::offline::Waveform::DcOffset)) {
        return ET_SIGNAL_GENERATOR_INVALID_CONFIG;
    }

    try {
        const et::offline::SignalGeneratorConfig native_config{
            static_cast<et::offline::Waveform>(config->waveform),
            config->sample_rate_hz,
            config->frequency_hz,
            config->sweep_start_hz,
            config->sweep_stop_hz,
            config->amplitude,
            config->seed,
            config->symbol_rate_hz,
        };
        auto* output = reinterpret_cast<et::offline::ComplexI8*>(interleaved_iq);
        et::offline::SignalGenerator generator(native_config);
        generator.generate(output, complex_count);
        return ET_SIGNAL_GENERATOR_OK;
    } catch (const std::invalid_argument&) {
        return ET_SIGNAL_GENERATOR_INVALID_CONFIG;
    } catch (...) {
        return ET_SIGNAL_GENERATOR_INVALID_ARGUMENT;
    }
}
