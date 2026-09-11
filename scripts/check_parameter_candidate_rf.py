"""KTR-4.2-F1: adayın kayıtlı fiziksel AM/FM regresyonu; kör kabul değildir."""
from pathlib import Path
import sys,json,hashlib
from collections import Counter
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.operator_console.measurement_record import read_measurement
from algorithms.parameters.refined_candidate import measure_candidate,classify_candidate


def run(folder):
    model=json.loads((folder/'candidate-model.json').read_text(encoding='utf-8'));rows=[]
    for family,name in [('AM','parameter-rf-am735-analysis24-20260909'),('FM','parameter-rf-735-analysis24-20260909')]:
        records=ROOT/'build/acceptance'/name/'records'
        paths=sorted(records.glob('*.zip'))
        if len(paths)!=20:raise ValueError('Her aile için 20 özgün kayıt gerekli; eksik kayıt başarı sayılmaz.')
        for path in paths:
            doc,frames=read_measurement(path);span=doc['intent']['span']
            result=measure_candidate(frames,sample_rate_hz=doc['sample_rate_hz'],center_frequency_hz=doc['center_frequency_hz'],
                lower_bin=span['lower_shifted_bin'],upper_bin=span['upper_shifted_bin'])
            rows.append({'source':str(path.relative_to(ROOT)),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'family':family,'decision':classify_candidate(result,model),'measurement':asdict(result)})
    report={'model_sha256':hashlib.sha256((folder/'candidate-model.json').read_bytes()).hexdigest(),
        'source_sha256':hashlib.sha256((ROOT/'algorithms/parameters/refined_candidate.py').read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'summary':{kind:dict(Counter(r['decision'] for r in rows if r['family']==kind)) for kind in ['AM','FM']},
        'rows':rows,'acceptance':False,'limits':'Previously inspected RF regression; float preprocessing, synthetic event ownership, no FPGA; not independent blind RF.'}
    with (folder/'rf-check.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
    print(json.dumps(report['summary'],ensure_ascii=False))


if __name__=='__main__':run(Path(sys.argv[1]))
