"""PÇ-02/03 geliştirme adayı; ürün profilinde etkin değildir (KTR-4.2-F1).

16.384 örnek spektrumu ve bant ölçekli özellikler. Eski F5 baytları korunur.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class CandidateMeasurement:
    center_hz: float | None
    line_hz: float | None
    obw99_hz: float | None
    power_dbfs: float | None
    snr_db: float | None
    reason: str | None
    features: tuple[float, ...] = ()
    bandwidth_reason: str | None = None


def classify_candidate(measurement, model):
    """Açık JSON ağaçları; yürütülebilir model yüklemez. Ürün yetkisi vermez."""
    if measurement.reason or not measurement.features:
        return "Belirsiz"
    vector=np.asarray(measurement.features,dtype=np.float32)
    if not np.all(np.isfinite(vector)):
        return "Belirsiz"
    probabilities=np.zeros(len(model['classes']))
    for tree in model['trees']:
        node=0
        for _ in range(len(tree['left'])):
            if tree['left'][node]<0:
                values=np.asarray(tree['value'][node],dtype=float)
                probabilities+=values/max(values.sum(),1e-30)
                break
            node=tree['left'][node] if vector[tree['feature'][node]]<=tree['threshold'][node] else tree['right'][node]
        else:
            raise ValueError("Geçersiz aday model ağacı.")
    probabilities/=max(len(model['trees']),1)
    analog=sum(p for p,c in zip(probabilities,model['classes']) if c in ('AM','NFM'))
    digital=sum(p for p,c in zip(probabilities,model['classes']) if c in ('OOK','FSK','BPSK','QPSK','QAM'))
    if analog>=model['threshold']:return 'Analog'
    if digital>=model['threshold']:return 'Sayısal'
    return 'Belirsiz'


def _entropy(power):
    p = np.maximum(np.asarray(power, dtype=float), 0)
    p = p / max(float(p.sum()), 1e-30)
    return float(-np.sum(p * np.log(np.maximum(p, 1e-30))) / math.log(max(2, p.size)))


def _stats(values):
    x = np.asarray(values, dtype=float)
    x = x - np.mean(x)
    sd = max(float(np.std(x)), 1e-12)
    x = x / sd
    return [float(np.mean(x**3)), float(np.mean(x**4)),
            float(np.mean(np.abs(np.diff(x)))),
            _entropy(abs(np.fft.rfft(x * np.hanning(len(x))))**2)]


def measure_candidate(samples, *, sample_rate_hz, center_frequency_hz, lower_bin, upper_bin):
    """İzole span için tanı; olay sahipliği ve kart kabulünü iddia etmez."""
    frames = np.asarray(samples, dtype=np.complex128)
    if frames.shape != (4, 4096) or not np.all(np.isfinite(frames)):
        raise ValueError("Dört sonlu 4096 örnekli kare gerekli.")
    if not math.isfinite(sample_rate_hz) or sample_rate_hz <= 0 or not math.isfinite(center_frequency_hz):
        raise ValueError("Frekans bağlamı geçersiz.")
    if not 56 <= lower_bin < upper_bin <= 4039 or not 8 <= upper_bin-lower_bin+1 <= 512:
        raise ValueError("İzole aralık ve iki taraflı referans gerekli.")
    if np.any(abs(frames.real) >= 127/128) or np.any(abs(frames.imag) >= 127/128):
        return CandidateMeasurement(None, None, None, None, None, "clipped_iq")
    x=frames.ravel(); n=len(x); win=np.hanning(n)
    # Constant receiver DC is not emission power; an on-LO target is ambiguous.
    x=x-np.mean(x)
    psd=abs(np.fft.fftshift(np.fft.fft(x*win)))**2/(sample_rate_hz*np.sum(win*win))
    df=sample_rate_hz/n
    lo,hi=lower_bin*4,upper_bin*4+3
    left=psd[lo-144:lo-20]; right=psd[hi+21:hi+145]
    # Exponential single-periodogram noise median correction.
    nl,nr=float(np.median(left)/np.log(2)),float(np.median(right)/np.log(2))
    noise=max((nl+nr)/2,1e-30)
    if min(nl,nr)<=0 or abs(10*np.log10(nl/nr))>6:
        return CandidateMeasurement(None,None,None,None,None,"reference_mismatch")
    signed=psd[lo:hi+1]-noise
    total=float(signed.sum())
    snr=10*np.log10(max(total,1e-30)/(noise*len(signed)))
    if snr<6:
        return CandidateMeasurement(None,None,None,None,float(snr),"low_snr")
    # Equal-tail OBW99 requires each tail outside the span to stay below 0.5%.
    # Outside energy cannot be attributed to this emitter; conservatively refuse
    # full-emission OBW when even the upper noise-uncertainty bound exceeds 1%.
    outside_tails=(psd[80:lo],psd[hi+1:-80])
    far=np.concatenate((psd[80:max(80,lo-1024)],psd[min(n-80,hi+1025):-80]))
    bandwidth_reason=None
    if far.size<128:
        bandwidth_reason="bandwidth_reference_unavailable"
    else:
        # A signal tail may contaminate the pooled far reference. Use the
        # lowest of disjoint reference medians as a conservative noise floor;
        # this can abstain on colored noise rather than erase emission tails.
        reference_blocks=np.array_split(far,8)
        outside_noise=max(min(float(np.median(block)/np.log(2)) for block in reference_blocks),1e-30)
        # Hann bins are correlated: window fourth-moment inflation, not an
        # independent-bin variance assumption. This remains a diagnostic bound.
        inflation=n*float(np.sum(win**4))/float(np.sum(win**2))**2
        for outside in outside_tails:
            excess=float(outside.sum()-outside_noise*outside.size)
            reference_size=min(block.size for block in reference_blocks)
            uncertainty=3*outside_noise*math.sqrt(inflation*(outside.size+outside.size**2/reference_size/(math.log(2)**2)))
            if max(0.,excess)+uncertainty>.005*total:
                bandwidth_reason="outside_energy_or_noise_uncertainty"
    # Candidate denoising is explicitly empirical, not a standards claim.
    weights=np.maximum(signed-3*noise,0)
    if weights.sum()<=0:
        return CandidateMeasurement(None,None,None,None,float(snr),"no_support")
    cdf=np.cumsum(weights)/weights.sum()
    bins=np.arange(lo,hi+1)
    edge=np.interp([.005,.995],cdf,bins)
    if edge[0]<lo+4 or edge[1]>hi-4:
        return CandidateMeasurement(None,None,None,None,float(snr),"span_edge")
    centroid=float(np.sum(bins*weights)/weights.sum())
    peak=lo+int(np.argmax(weights)); logs=np.log(np.maximum(psd[peak-1:peak+2],1e-30))
    if abs(peak-n/2)<=4:
        return CandidateMeasurement(None,None,None,None,float(snr),"dc_ambiguous")
    denom=logs[0]-2*logs[1]+logs[2]
    delta=float(np.clip(.5*(logs[0]-logs[2])/denom,-.5,.5)) if abs(denom)>1e-15 else 0.
    line_share=float(np.sum(weights[max(0,peak-lo-2):peak-lo+3])/weights.sum())
    # A strong stable line is only a line candidate; carrier applicability is separate.
    line=center_frequency_hz+(peak+delta-n/2)*df if line_share>.25 else None
    width=max(float(edge[1]-edge[0]),4.)
    # Isolate measured support with margin, mix to centroid, and reduce bandwidth.
    fft=np.fft.fftshift(np.fft.fft(x))
    keep=(np.arange(n)>=max(lo,math.floor(edge[0]-width*.25))) & (np.arange(n)<=min(hi,math.ceil(edge[1]+width*.25)))
    filtered=np.fft.ifft(np.fft.ifftshift(fft*keep))
    feature_center=peak+delta if line is not None else centroid
    filtered*=np.exp(-2j*np.pi*(feature_center-n/2)*np.arange(n)/n)
    stride=max(1,int(n/(8*width)))
    channel=filtered[256:-256:stride]
    envelope=np.abs(channel); rms=math.sqrt(max(float(np.mean(envelope**2)),1e-30)); z=channel/rms
    amp=abs(z); phase=np.angle(z[1:]*z[:-1].conj())
    features=[float(np.std(amp)/max(np.mean(amp),1e-12)),float(np.mean(amp<.25)),
        float(np.mean(amp**4)),float(abs(np.mean(z*z))),float(abs(np.mean(z**4))),
        float(line_share),float(np.std(phase)),float(np.mean(abs(phase)>1)),
        *_stats(amp),*_stats(phase),_entropy(weights),
        float(abs(np.mean(z))/max(np.mean(abs(z)),1e-20))]
    for lag in (1,2,4,8):
        a=amp-np.mean(amp); b=phase-np.mean(phase)
        features.extend([float(np.mean(a[lag:]*a[:-lag])/max(np.mean(a*a),1e-20)),
                         float(np.mean(b[lag:]*b[:-lag])/max(np.mean(b*b),1e-20))])
    return CandidateMeasurement(center_frequency_hz+(centroid-n/2)*df,line,
        float((edge[1]-edge[0])*df) if bandwidth_reason is None else None,
        float(10*np.log10(total*df)),float(snr),None,tuple(features),bandwidth_reason)
