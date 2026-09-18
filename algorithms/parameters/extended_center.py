"""Uzun ölçümün geniş bant merkezi ve çift grup-jackknife kararlılık tanısı.

Bağımsız doğrulama modeli; ürün sayısal hesabı ARM'da kalır.
"""
import numpy as np


def extended_center_reference(samples, lower, upper):
    values = np.asarray(samples, dtype=complex)
    if values.shape != (16, 4096) or not np.all(np.isfinite(values)):
        raise ValueError("16 sonlu I/Q karesi gerekir.")
    if not 56 <= lower <= upper <= 4039 or upper - lower + 1 < 100:
        raise ValueError("Geniş bant analiz aralığı gerekir.")
    hann = .5 - .5 * np.cos(2 * np.pi * np.arange(4096) / 4096)
    rectangular = np.fft.fftshift(np.fft.fft(values, axis=1), axes=1)
    psd = abs(np.fft.fftshift(np.fft.fft(values * hann, axis=1), axes=1)) ** 2

    def center(indices):
        selected = rectangular[indices]
        power = abs(selected) ** 2
        noise = (power[:, lower-36:lower-4].mean(axis=1)
                 + power[:, upper+5:upper+37].mean(axis=1)) / 2
        support = np.flatnonzero(power.mean(axis=0)[lower:upper+1] >= 6 * noise.mean())
        if support.size:
            lo, hi = lower + support[0], lower + support[-1]
        else:
            average = psd[indices].mean(axis=0)
            n = (average[lower-36:lower-4].mean() + average[upper+5:upper+37].mean()) / 2
            weights = np.maximum(np.convolve(average[lower:upper+1]-n, [.25,.5,.25], 'same')
                                 - 2.5*n/np.sqrt(len(indices))*np.sqrt(.375), 0)
            cumulative = np.cumsum(weights)
            if cumulative[-1] <= 0:
                raise ValueError("Pozitif bant enerjisi yok.")
            def edge(q):
                i = np.searchsorted(cumulative, q*cumulative[-1])
                before = cumulative[i-1] if i else 0
                return lower+i-.5+(q*cumulative[-1]-before)/weights[i]
            lo, hi = max(lower, int(np.ceil(edge(.005)+.5))), min(upper, int(np.floor(edge(.995)-.5)))
        band = selected[:, lo:hi+1]
        amplitude = np.sqrt(np.maximum(power[:, lo:hi+1].mean(axis=1)-noise, 0))
        denoised = np.zeros_like(selected)
        denoised[:, lo:hi+1] = amplitude[:, None]*band/np.maximum(abs(band), np.finfo(float).tiny)
        reconstructed = np.fft.ifft(np.fft.ifftshift(denoised, axes=1), axis=1)
        broad = (abs(np.fft.fftshift(np.fft.fft(reconstructed*hann, axis=1), axes=1))**2).mean(axis=0)[lower:upper+1]
        return float(np.dot(np.arange(lower, upper+1), broad)/broad.sum())

    indices = np.arange(16)
    complete = center(indices)
    subsets = np.array([center(np.delete(indices, np.s_[i*4:(i+1)*4])) for i in range(4)])
    broad_uncertainty = float(np.sqrt(.75*np.sum((subsets-subsets.mean())**2)))

    def centroid(indices):
        average = psd[indices].mean(axis=0)
        noise = (average[lower-36:lower-4].mean()
                 + average[upper+5:upper+37].mean()) / 2
        weights = average[lower:upper+1] - noise
        if weights.sum() <= 0:
            raise ValueError("Pozitif bant enerjisi yok.")
        return float(np.dot(np.arange(lower, upper+1), weights) / weights.sum())

    centroid_subsets = np.array([
        centroid(np.delete(indices, np.s_[i*4:(i+1)*4])) for i in range(4)
    ])
    centroid_uncertainty = float(np.sqrt(
        .75*np.sum((centroid_subsets-centroid_subsets.mean())**2)
    ))
    uncertainty = min(broad_uncertainty, centroid_uncertainty)
    return {"center_bin": complete, "center_uncertainty_bins": uncertainty,
            "broad_uncertainty_bins": broad_uncertainty,
            "centroid_uncertainty_bins": centroid_uncertainty,
            "valid": bool(np.isfinite(uncertainty) and uncertainty <= 4)}
