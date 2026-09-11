"""KTR-4.2-F1: aday karar paydaları, JSON yürütücüsü ve kapsam dışı kapılar."""
from pathlib import Path
import sys,json,hashlib
from dataclasses import asdict
from collections import Counter
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from algorithms.parameters.refined_candidate import CandidateMeasurement,measure_candidate,classify_candidate


def verify(folder):
    report=json.loads((folder/'report.json').read_text(encoding='utf-8'))
    model=json.loads((folder/'candidate-model.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((folder/'candidate-model.json').read_bytes()).hexdigest()==report['model_sha256_before_test']
    families={};equivalent=True
    for family in report['test_matrix']:
        rows=[r for r in report['test_rows'] if r['truth']['family']==family]
        expected='Analog' if family in ('AM','NFM') else 'Belirsiz' if family=='CW' else 'Sayısal'
        count=Counter()
        for row in rows:
            decision=classify_candidate(CandidateMeasurement(**row['result']),model)
            equivalent &= decision==row['decision']
            count['correct' if decision==expected else 'abstained' if decision=='Belirsiz' else 'wrong']+=1
        coverage=(count['correct']+count['wrong'])/len(rows)
        precision=count['correct']/max(count['correct']+count['wrong'],1)
        power_errors=[abs(r['result']['power_dbfs']-r['truth']['power_dbfs']) for r in rows if r['result']['power_dbfs'] is not None]
        line_errors=[abs(r['result']['line_hz']-(700000000+r['truth']['offset_hz'])) for r in rows if r['result']['line_hz'] is not None] if family in ('CW','AM') else []
        families[family]={'total':len(rows),**count,'coverage':coverage,'precision':precision,
            'power_valid':len(power_errors),'power_error_q95_db':float(np.quantile(power_errors,.95)) if power_errors else None,
            'line_valid':len(line_errors),'line_error_q95_hz':float(np.quantile(line_errors,.95)) if line_errors else None,
            'domain_gate': count['correct']==len(rows) if family=='CW' else coverage>=.8 and precision>=.9}
    negatives=[];t=np.arange(16384)/2000000
    for seed in range(20):
        rng=np.random.default_rng(10100000+seed);noise=.005*(rng.normal(size=len(t))+1j*rng.normal(size=len(t)))
        waves={'noise':noise,'chirp':.1*np.exp(2j*np.pi*(40000*t+500000*t*t))+noise,
            'two_tones':.08*(np.exp(2j*np.pi*30000*t)+np.exp(2j*np.pi*70000*t))+noise}
        for name,x in waves.items():
            result=measure_candidate(x.reshape(4,4096),sample_rate_hz=2000000,center_frequency_hz=700000000,lower_bin=1920,upper_bin=2390)
            negatives.append({'kind':name,'seed':seed,'decision':classify_candidate(result,model),'reason':result.reason})
    false_definite=sum(r['decision']!='Belirsiz' for r in negatives)
    result={'requirements':['KTR-4.2','KTR-4.2-F1'],'model_equivalence':equivalent,'families':families,
        'negative_controls':negatives,'negative_false_definite':false_definite,
        'software_domain_gate':equivalent and all(f['domain_gate'] for f in families.values()) and false_definite==0,
        'product_acceptance':False,'hardware_acceptance':False,
        'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with (folder/'verification.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='negative_controls'},ensure_ascii=False,indent=2))
    return result['software_domain_gate']


if __name__=='__main__':sys.exit(0 if verify(Path(sys.argv[1])) else 1)
