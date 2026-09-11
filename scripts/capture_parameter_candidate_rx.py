"""KTR-4.2: sonlu RX ve dondurulmuş aday ölçümü; TX/FPGA kullanmaz."""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import asdict
from collections import Counter
import argparse,sys,json,subprocess,hashlib
import numpy as np
from scipy.signal import resample_poly
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from algorithms.parameters.refined_candidate import measure_candidate,classify_candidate


def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    model_bytes=args.model.read_bytes()
    if hashlib.sha256(model_bytes).hexdigest()!=args.model_sha256:
        raise ValueError('Model özeti eşleşmiyor.')
    model=json.loads(model_bytes);rows=[]
    for center in (args.frequency_hz+300000,args.frequency_hz-300000):
        raw=args.output/f'rx-{center}.ci8'
        command=[args.tool,'-d',args.serial,'-r',str(raw.resolve()),'-f',str(center),'-s','8000000',
            '-n','4000000','-l',str(args.gain_db),'-g',str(args.gain_db),'-a','0','-p','0','-B']
        started=datetime.now(timezone.utc).isoformat()
        process=subprocess.run(command,capture_output=True,timeout=15)
        log=(process.stdout+process.stderr).decode('utf-8',errors='replace')
        raw.with_suffix('.log').write_text(log,encoding='utf-8')
        data=raw.read_bytes() if raw.exists() else b''
        capture={'started_utc':started,'command':command,'returncode':process.returncode,
            'raw_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
            'external_tx_state':args.tx_state,'source_settings':args.source_settings}
        raw.with_suffix('.json').write_text(json.dumps(capture,ensure_ascii=False,indent=2),encoding='utf-8')
        if process.returncode or len(data)!=8000000:
            raise RuntimeError('Alım tamamlanmadı; ham kayıt ve günlük korunuyor.')
        v=np.frombuffer(data,dtype=np.int8)[1048576:]
        rail=float(np.mean((v<=-128)|(v>=127)))
        if rail>0:
            raise RuntimeError('Yerleşmiş alımda kırpılma var; yüksek kazanca geçilmez.')
        x=(v[::2].astype(float)+1j*v[1::2].astype(float))/128
        iq=resample_poly(x,1,4)[256:-256]
        peak=round(2048+(args.frequency_hz-center)/(2000000/4096))
        results=[]
        for i in range(10):
            frames=iq[i*16384:(i+1)*16384].reshape(4,4096)
            measurement=measure_candidate(frames,sample_rate_hz=2000000,center_frequency_hz=center,
                lower_bin=peak-100,upper_bin=peak+100)
            results.append({'window':i,'measurement':asdict(measurement),'decision':classify_candidate(measurement,model)})
        rows.append({'capture':capture,'rail_fraction':rail,'results':results})
    report={'requirements':['KTR-4.2','KTR-4.2-F1'],'model_sha256':args.model_sha256,
        'source_sha256':hashlib.sha256((ROOT/'algorithms/parameters/refined_candidate.py').read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rows':rows,
        'summary':dict(Counter(r['decision'] for row in rows for r in row['results'])),
        'fpga_exercised':False,'product_acceptance':False,'dbm_calibrated':False,
        'preprocessing':'discard 524288 complex raw samples; CI8/128; resample_poly 1:4; trim 256; ten nonoverlapping windows',
        'limits':'Two RF runs; windows are not independent runs. Known source supplied only for capture tuning, not classification.'}
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report['summary'],ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--model-sha256',required=True)
    parser.add_argument('--frequency-hz',type=int,required=True)
    parser.add_argument('--gain-db',type=int,choices=(0,8,16,24),default=16)
    parser.add_argument('--serial',required=True)
    parser.add_argument('--tool',required=True)
    parser.add_argument('--tx-state',required=True)
    parser.add_argument('--source-settings',required=True)
    run(parser.parse_args())
