"""KTR-4.2: bağımsız uzun temiz I/Q ile sayısal aday doğrulaması."""
from pathlib import Path
import argparse
import sys,json,hashlib
from dataclasses import asdict
import numpy as np
from scipy.signal import fftconvolve,firwin
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from algorithms.parameters.refined_candidate import measure_candidate


def waveform(family,seed,snr):
    rng=np.random.default_rng(seed);fs=2_000_000;n=262144;t=np.arange(n)/fs
    offset=rng.uniform(40000,140000);tone=rng.uniform(700,3700)
    if family=='CW':base=np.ones(n)
    elif family=='AM':base=1+.75*np.cos(2*np.pi*tone*t+.31)
    elif family=='NFM':base=np.exp(1j*2.2*np.sin(2*np.pi*tone*t+.71))
    else:
        sps=int(rng.integers(60,150));count=(n+16*sps)//sps+1
        if family=='QPSK':symbols=(rng.choice([-1,1],count)+1j*rng.choice([-1,1],count))/np.sqrt(2)
        else:symbols=rng.choice([-1,1],count)
        if family=='FSK':base=np.exp(2j*np.pi*np.cumsum(np.repeat(symbols,sps)[:n])*(fs/sps)*.5/fs)
        elif family=='BPSK_RECT':base=np.repeat(symbols,sps)[:n]
        else:
            base=fftconvolve(np.repeat(symbols,sps),firwin(12*sps+1,1.1/sps,window='blackman'),mode='same')[6*sps:6*sps+n]
    clean=np.asarray(base*np.exp(2j*np.pi*offset*t),dtype=complex)
    clean*=.12/np.sqrt(np.mean(abs(clean)**2))
    w=np.hanning(n);power=abs(np.fft.fftshift(np.fft.fft(clean*w)))**2
    freq=np.fft.fftshift(np.fft.fftfreq(n,1/fs));cdf=np.cumsum(power)/power.sum()
    edges=np.interp([.005,.995],cdf,freq)
    start=32768;part=clean[start:start+16384];noise=np.sqrt(np.mean(abs(part)**2)/10**(snr/10)/2)*(rng.normal(size=len(part))+1j*rng.normal(size=len(part)))
    peak=round(2048+offset/(fs/4096));lo,hi=peak-230,peak+230
    return (part+noise).reshape(4,4096),{'family':family,'seed':seed,'snr_db':snr,
        'offset_hz':offset,'obw99_hz':float(edges[1]-edges[0]),'edges_hz':edges.tolist(),
        'power_dbfs':float(10*np.log10(np.mean(abs(part)**2))),'lower_bin':lo,'upper_bin':hi,
        'full_emission_in_span':bool(edges[0]>=(lo-2048)*fs/4096 and edges[1]<=(hi-2048)*fs/4096)}


def run(out, seed_base=23000000):
    out.mkdir(parents=True,exist_ok=False);rows=[]
    for fi,family in enumerate(('CW','AM','NFM','FSK','BPSK','QPSK','BPSK_RECT')):
        for snr in (12,24,36):
            for i in range(8):
                frames,truth=waveform(family,seed_base+fi*1000+i,snr)
                r=measure_candidate(frames,sample_rate_hz=2000000,center_frequency_hz=700000000,lower_bin=truth['lower_bin'],upper_bin=truth['upper_bin'])
                rows.append({'reference':truth,'measurement':asdict(r),
                    'obw_error_hz':None if r.obw99_hz is None else r.obw99_hz-truth['obw99_hz'],
                    'power_error_db':None if r.power_dbfs is None else r.power_dbfs-truth['power_dbfs']})
    summary={}
    for family in ('CW','AM','NFM','FSK','BPSK','QPSK','BPSK_RECT'):
        sub=[r for r in rows if r['reference']['family']==family];valid=[r for r in sub if r['obw_error_hz'] is not None]
        summary[family]={'total':len(sub),'obw_valid':len(valid),
            'obw_tolerance_pass':sum(abs(r['obw_error_hz'])<=max(2*2000000/4096,.1*r['reference']['obw99_hz']) for r in valid),
            'obw_max_absolute_error_hz':max((abs(r['obw_error_hz']) for r in valid),default=None),
            'outside_span_total':sum(not r['reference']['full_emission_in_span'] for r in sub),
            'outside_span_false_valid':sum(not r['reference']['full_emission_in_span'] for r in valid)}
    report={'requirements':['KTR-4.2','KTR-4.2-F1'],'seed_base':seed_base,'summary':summary,'rows':rows,'acceptance':False,
        'limits':['Independent generator; finite long-record reference','Shared seed across SNR is not independent waveform','No live product, no hardware acceptance'],
        'source_hashes':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('scripts/validate_candidate_numeric.py','algorithms/parameters/refined_candidate.py')}}
    with (out/'report.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--seed-base',type=int,default=23000000)
    args=parser.parse_args()
    run(args.output,args.seed_base)
