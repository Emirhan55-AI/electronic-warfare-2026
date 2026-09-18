"""Kayıtlı I/Q üzerinde salt okunur parametre ve sınıflandırıcı incelemesi."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from app.operator_console.measurement_record import read_measurement
from algorithms.spectrum import SpectrumConfig, SpectrumProcessor
from digital_analog_detection.integration import classify_parameter_frames
from verify_p0_parameter_runtime import _build, _ci8

IDS = ("15c7774e15594edb8bae9e73429b43e5", "a2f955bbea2f40dd87360498e91e0b4f")
DIRECTORY = Path(os.environ["LOCALAPPDATA"]) / "TEKNOFEST 2026 Elektronik Harp" / "BÂZ" / "parameter-records"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"requirements": ["KTR-4.2", "KTR-4.2-F1"],
              "physical_execution": False, "rf_accuracy_acceptance": False,
              "records": [], "source_sha256": {}}
    with tempfile.TemporaryDirectory(prefix="parameter-review-") as raw:
        directory = Path(raw)
        executable, _, compiler = _build(directory)
        report["compiler"] = compiler
        for record_id in IDS:
            path = DIRECTORY / f"{record_id}.zip"
            document, frames = read_measurement(path)
            span = document["intent"]["span"]
            lo, hi = span["lower_shifted_bin"], span["upper_shifted_bin"]
            fs = document["sample_rate_hz"]
            processor = SpectrumProcessor(SpectrumConfig(**document["spectrum_config"]))
            paths = []
            for i, frame in enumerate(frames):
                iq, decoded = _ci8(frame)
                assert np.array_equal(decoded, frame)
                spectrum = processor.process(decoded, sample_rate_hz=fs,
                    center_frequency_hz=document["center_frequency_hz"])
                power = np.rint(np.asarray(spectrum.fft_power_unshifted) * (1 << 30)).astype("<u8")
                ip, pp = directory / f"{i}.ci8", directory / f"{i}.u64"
                ip.write_bytes(iq)
                pp.write_bytes(power.tobytes())
                paths.extend((ip, pp))
            variants = []
            # Sabit, önceden tanımlı aralıklar; başarılı sonucu seçme veya ürün ayarı yoktur.
            for margin in (0, 64, 128, 256):
                lower, upper = max(56, lo - margin), min(4039, hi + margin)
                output = directory / "numeric.json"
                subprocess.run([str(executable), str(int(fs)),
                    str(int(document["center_frequency_hz"])), str(lower), str(upper),
                    *map(str, paths), str(output)], check=True, capture_output=True)
                result = json.loads(output.read_text(encoding="utf-8"))
                variants.append({"margin_bins": margin, "span": [lower, upper], "result": result})
            mapping = {"emission_center_frequency_hz": "emission_center_frequency",
                       "carrier_line_frequency_hz": "carrier_line_frequency",
                       "occupied_bandwidth_hz": "occupied_bandwidth",
                       "channel_power_dbfs": "channel_power_dbfs", "snr_estimate_db": "snr_estimate_db"}
            states = {"valid": 1, "insufficient_quality": 2, "uncertain": 3, "not_observed": 4}
            for key, field in mapping.items():
                original, replay = document["fields"][field], variants[0]["result"][key]
                assert replay["state"] == states[original["state"]]
                if original["state"] == "valid":
                    assert abs(original["value"] - replay["value"]) < (4.0 if key.endswith("_hz") else .02)
            domain = classify_parameter_frames(frames, sample_rate_hz=fs,
                lower_shifted_bin=lo, upper_shifted_bin=hi,
                snr_db=document["fields"]["snr_estimate_db"]["value"])
            old_domain = document["automatic_signal_domain"]
            assert domain.model_sha256 == old_domain["model_sha256"]
            assert domain.value == old_domain["value"]
            assert abs(domain.confidence - old_domain["confidence"]) < 1e-12
            report["records"].append({"record_id": record_id,
                "record_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "iq_sha256": document["iq"]["sha256"], "requested_utc": document["requested_utc"],
                "sample_rate_hz": fs, "observation_duration_s": document["observation_duration_s"],
                "original_span": span, "original_fields": document["fields"],
                "original_quality": document["quality"], "classification_replay": domain.as_record(),
                "numeric_replay_variants": variants,
                "running_service_identity": document["board_measurement"]["service_identity_reason"]})

    # Hedef AM değişmez. Analiz aralığı dışındaki komşu enerjiye duyarlılık tanısı.
    fs, n = 2_000_000.0, 16384
    t = np.arange(n) / fs
    rng = np.random.default_rng(20260916)
    target = (1 + .65 * np.cos(2 * np.pi * 1800 * t)) * np.exp(2j * np.pi * 25000 * t)
    noise = .01 * (rng.normal(size=n) + 1j * rng.normal(size=n))
    symbols = np.repeat(rng.choice((-1., 1.), size=(n + 19) // 20), 20)[:n]
    neighbor = symbols * np.exp(2j * np.pi * 220000 * t)
    report["synthetic_neighbor_probe"] = []
    for amplitude in (0., .25, .5, 1., 2., 4.):
        signal = target + noise + amplitude * neighbor
        result = classify_parameter_frames(tuple(signal.reshape(4, 4096)), sample_rate_hz=fs,
            lower_shifted_bin=2030, upper_shifted_bin=2170, snr_db=20.)
        report["synthetic_neighbor_probe"].append({"neighbor_amplitude": amplitude,
            "note": "SNR tanı için sabit girdidir; bağımsız RF ölçümü değildir.", **result.as_record()})
    report["synthetic_narrow_fm_probe"] = []
    for deviation in (2500., 5000., 10000.):
        for snr in (10., 20., 30.):
            clean = np.exp(2j * np.pi * 25000 * t + 1j * deviation / 1800 * np.sin(2 * np.pi * 1800 * t))
            local_rng = np.random.default_rng(20260916)
            noisy = clean + np.sqrt(10 ** (-snr / 10) / 2) * (local_rng.normal(size=n) + 1j * local_rng.normal(size=n))
            result = classify_parameter_frames(tuple(noisy.reshape(4, 4096)), sample_rate_hz=fs,
                lower_shifted_bin=2030, upper_shifted_bin=2170, snr_db=snr)
            report["synthetic_narrow_fm_probe"].append({"truth": "Analog", "deviation_hz": deviation,
                "injected_snr_db": snr, "note": "Tek tohumlu kapsam tanısı; başarı oranı değildir.", **result.as_record()})
    for relative in ("platforms/embedded/p0/src/p0_parameter_runtime.c",
                     "digital_analog_detection/integration.py", "digital_analog_detection/classifier_model.py",
                     "digital_analog_detection/feature_extractor_v1.py", "digital_analog_detection/train_classifier.py",
                     "app/operator_console/quick_measurement_actions.py",
                     "output/parameter-review-20260916/reproduce.py"):
        report["source_sha256"][relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    destination = args.output
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(destination)
    for record in report["records"]:
        print(record["record_id"], [(v["margin_bins"], v["result"]["quality"]["temporal_edge_range_bins"]) for v in record["numeric_replay_variants"]])
    print("neighbor", [(r["neighbor_amplitude"], r["state"], r["value"], r["confidence"]) for r in report["synthetic_neighbor_probe"]])
    print("NFM", [(r["deviation_hz"], r["injected_snr_db"], r["value"], r["confidence"]) for r in report["synthetic_narrow_fm_probe"]])


if __name__ == "__main__":
    main()
