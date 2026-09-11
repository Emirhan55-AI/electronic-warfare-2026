"""KTR-4.2-F1: dondurulmuş modelle güncel adayın tam regresyonu."""
from pathlib import Path
import sys,json,hashlib,shutil
from dataclasses import asdict
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from algorithms.parameters.refined_candidate import measure_candidate,classify_candidate
from scripts.develop_parameter_candidate import make_signal
from scripts.validate_parameter_bench import signal
from scripts.check_parameter_candidate_rf import run as check_rf


def run(frozen,output):
    output.mkdir(parents=True,exist_ok=False)
    original=json.loads((frozen/'report.json').read_text(encoding='utf-8'))
    shutil.copyfile(frozen/'candidate-model.json',output/'candidate-model.json')
    model=json.loads((output/'candidate-model.json').read_text(encoding='utf-8'))
    rows=[]
    for old in original['test_rows']:
        samples,truth=make_signal(old['truth']['family'],old['truth']['seed'])
        if truth!=old['truth']:raise ValueError('Dondurulmuş üretici bağlamı değişti.')
        r=measure_candidate(samples,sample_rate_hz=2000000,center_frequency_hz=700000000,
            lower_bin=truth['lower'],upper_bin=truth['upper'])
        decision=classify_candidate(r,model)
        rows.append({'truth':truth,'measurement':asdict(r),'decision':decision,'previous_decision':old['decision']})
    bench=[]
    for family in ('CW','AM','NFM','BPSK','FSK'):
        for snr in (12,24):
            for seed in (73001,73002,73003):
                frames,truth=signal(family,seed,snr)
                r=measure_candidate(frames,sample_rate_hz=2000000,center_frequency_hz=700000000,lower_bin=1978,upper_bin=2438)
                bench.append({'family':family,'seed':seed,'snr':snr,'reference':truth,'measurement':asdict(r),
                    'decision':classify_candidate(r,model),'obw_error_hz':None if r.obw99_hz is None else r.obw99_hz-truth['obw99_hz']})
    summary={family:{'total':sum(r['truth']['family']==family for r in rows),
        'bandwidth_valid':sum(r['truth']['family']==family and r['measurement']['obw99_hz'] is not None for r in rows)}
        for family in original['test_matrix']}
    report={'requirements':['KTR-4.2','KTR-4.2-F1'],'model_sha256':hashlib.sha256((output/'candidate-model.json').read_bytes()).hexdigest(),
        'frozen_report_sha256':hashlib.sha256((frozen/'report.json').read_bytes()).hexdigest(),
        'decision_changes':sum(r['decision']!=r['previous_decision'] for r in rows),'summary':summary,
        'rows':rows,'independent_bench':bench,'acceptance':False,
        'remaining':'BPSK full-emission containment not reliable in all records; no independent OBW gate, product or ARM acceptance',
        'source_hashes':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
            'algorithms/parameters/refined_candidate.py','scripts/develop_parameter_candidate.py',
            'scripts/revalidate_parameter_candidate.py','scripts/validate_parameter_bench.py')}}
    with (output/'regression.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
    check_rf(output)
    print(json.dumps({'decision_changes':report['decision_changes'],'summary':summary},indent=2))


if __name__=='__main__':run(Path(sys.argv[1]),Path(sys.argv[2]))
