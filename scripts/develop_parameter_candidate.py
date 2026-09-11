"""KTR-4.2-F1: ayrı geliştirme/kalibrasyon/test tohumlarıyla aday değerlendirme."""
from pathlib import Path
import sys,json,hashlib
from dataclasses import asdict
from collections import Counter
import numpy as np
from scipy.signal import firwin, fftconvolve, resample_poly
from sklearn.ensemble import ExtraTreesClassifier

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from algorithms.parameters.refined_candidate import measure_candidate

FAMILIES=('CW','AM','NFM','OOK','FSK','BPSK','QPSK','QAM')
FS=2_000_000


def make_signal(family, seed):
    rng=np.random.default_rng(seed); n=65536; source_fs=8_000_000; t=np.arange(n)/source_fs
    offset=rng.uniform(-250000,250000); rate=rng.uniform(12000,45000)
    tone=rng.uniform(800,4500); depth=1. if seed%4==0 else rng.uniform(.35,1.)
    message=np.cos(2*np.pi*tone*t+rng.uniform(0,6.28))
    if seed%2:message=.7*message+.3*np.cos(2*np.pi*tone*1.73*t+rng.uniform(0,6.28))
    if family=='CW':base=np.ones(n,dtype=complex)
    elif family=='AM':base=1+depth*message
    elif family=='NFM':base=np.exp(2j*np.pi*np.cumsum(message*rng.uniform(2500,12000))/source_fs)
    else:
        sps=round(source_fs/rate); size=(n+8*sps)//sps+1
        if family in ('OOK','FSK','BPSK'):sym=rng.choice([-1,1],size)
        elif family=='QPSK':sym=np.exp(1j*(np.pi/4+np.pi/2*rng.integers(0,4,size)))
        else:sym=(rng.choice([-3,-1,1,3],size)+1j*rng.choice([-3,-1,1,3],size))/np.sqrt(10)
        if family=='FSK':base=np.exp(2j*np.pi*np.cumsum(np.repeat(sym,sps)[:n])*rate*.5/source_fs)
        else:
            if family=='OOK':sym=(sym+1)/2
            extended=np.repeat(sym,sps)
            taps=firwin(8*sps+1,1.2/sps)
            base=fftconvolve(extended,taps,mode='same')[4*sps:4*sps+n]
    clean=base*np.exp(2j*np.pi*offset*t)
    clean*=10**rng.uniform(-2.8,-.8)/np.sqrt(np.mean(abs(clean)**2))
    snr=rng.uniform(-4,32)
    noise=np.sqrt(np.mean(abs(clean)**2)/10**(snr/10)/2)*(rng.normal(size=n)+1j*rng.normal(size=n))
    observed=clean+noise
    # Independent receiver nuisance distribution; no captured RF used in fitting.
    observed=observed.real*(1+rng.uniform(-.05,.05))+1j*observed.imag
    observed+=rng.uniform(-.02,.02)+1j*rng.uniform(-.02,.02)
    if seed%3:
        observed=(np.clip(np.round(observed.real*128),-128,127)
                  +1j*np.clip(np.round(observed.imag*128),-128,127))/128
    peak=round(2048+offset/(FS/4096)); lower,upper=peak-240,peak+240
    observed=resample_poly(observed,1,4)
    return observed.reshape(4,4096),{'family':family,'seed':seed,'offset_hz':offset,'sample_rate_hz':FS,
        'power_dbfs':float(10*np.log10(np.mean(abs(clean)**2))),'lower':lower,'upper':upper}


def dataset(start, count):
    rows=[]
    for fi,family in enumerate(FAMILIES):
        for i in range(count):
            samples,truth=make_signal(family,start+fi*10000+i)
            result=measure_candidate(samples,sample_rate_hz=FS,center_frequency_hz=700000000,
                lower_bin=truth['lower'],upper_bin=truth['upper'])
            rows.append({'truth':truth,'result':asdict(result)})
    return rows


def main(out):
    out.mkdir(parents=True,exist_ok=False)
    train=dataset(18700000,480); calibration=dataset(19800000,80)
    good=[r for r in train if r['result']['features']]
    model=ExtraTreesClassifier(n_estimators=96,max_depth=12,min_samples_leaf=3,random_state=901,n_jobs=1)
    model.fit([r['result']['features'] for r in good],[r['truth']['family'] for r in good])
    # Fixed probability rejection; calibration is reported, never hidden as test.
    def evaluate(rows):
        matrix={f:Counter() for f in FAMILIES}
        for row in rows:
            features=row['result']['features']; decision='Belirsiz'
            if features:
                p=model.predict_proba([features])[0]
                analog=sum(p[i] for i,c in enumerate(model.classes_) if c in ('AM','NFM'))
                digital=sum(p[i] for i,c in enumerate(model.classes_) if c in ('OOK','FSK','BPSK','QPSK','QAM'))
                if analog>=.9:decision='Analog'
                elif digital>=.9:decision='Sayısal'
            row['decision']=decision;matrix[row['truth']['family']][decision]+=1
        return {k:dict(v) for k,v in matrix.items()}
    calibration_matrix=evaluate(calibration)
    model_doc={'classes':model.classes_.tolist(),'threshold':.9,'trees':[{'left':e.tree_.children_left.tolist(),
        'right':e.tree_.children_right.tolist(),'feature':e.tree_.feature.tolist(),'threshold':e.tree_.threshold.tolist(),
        'value':e.tree_.value[:,0,:].tolist()} for e in model.estimators_]}
    (out/'candidate-model.json').write_text(json.dumps(model_doc,separators=(',',':')),encoding='utf-8')
    frozen_hash=hashlib.sha256((out/'candidate-model.json').read_bytes()).hexdigest()
    test=dataset(20900000,100);test_matrix=evaluate(test)
    report={'requirements':['KTR-4.2','KTR-4.2-F1'],'candidate_only':True,'model_sha256_before_test':frozen_hash,
        'training_count':len(train),'training_usable':len(good),'calibration_matrix':calibration_matrix,
        'test_matrix':test_matrix,'test_rows':test,'calibration_rows':calibration,
        'source_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ['algorithms/parameters/refined_candidate.py','scripts/develop_parameter_candidate.py']},
        'acceptance':'not_complete; synthetic families only; RF, OOS, ARM and integration gates remain'}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'calibration':calibration_matrix,'test':test_matrix},ensure_ascii=False,indent=2))


if __name__=='__main__':main(Path(sys.argv[1]))
