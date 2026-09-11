"""KTR-4.2: yeni ön işlemeyi yalnız özgün gerçek RF pencereleriyle değerlendir."""
import argparse
import json
import os
from pathlib import Path
import sys
import zipfile
import numpy as np
import scipy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from algorithms.parameters.rf_observation import observe_rf
from analyze_parameter_rf_readiness import digest


def evaluate(output, captures_root):
    output.mkdir(parents=True,exist_ok=False)
    cases=[
        ('AM_new','teknofest-rx-am-linkcheck-20260909',14.2,8000,
         'parameter-am-linkcheck-20260909','capture'),
        ('AM_previous','teknofest-rx-newport-amg8-rx24-20260909',14.55,8000,
         'replay-amg8-evaluation-20260909','teknofest-rx-newport-amg8-rx24-20260909'),
        ('NFM','teknofest-rx-newport-nfmg8-rx24-20260909',21.75,24000,
         'replay-nfmg8-evaluation-20260909','capture'),
        ('BPSK','teknofest-rx-newport-bpskg8-rx24-20260909',20.60,32000,
         'replay-bpskg8-diagnostic-20260909','on'),
    ]
    report={'requirements':['KTR-4.2','KTR-4.2-F1'],
        'scope':'Gerçek RF geliştirme tanısı; sınıflandırıcı eğitim/başarı iddiası yok.',
        'source_sha256':{name:digest(ROOT/name) for name in
            ['algorithms/parameters/rf_observation.py','scripts/validate_rf_observation_records.py']},
        'runtime':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__},
        'physical_acceptance':False,'product_acceptance':False,'cases':[],'checks':{}}
    for label,folder,start,width,evidence_name,prefix in cases:
        capture_dir=captures_root/folder
        path=capture_dir/'rx.ci8'
        evidence_path=ROOT/'results/evidence/phase08'/f'{evidence_name}.json'
        evidence=json.loads(evidence_path.read_text(encoding='utf-8'))
        if not path.exists():
            capture_dir=output/'recovered'/folder
            capture_dir.mkdir(parents=True,exist_ok=False)
            with zipfile.ZipFile(evidence_path.with_suffix('.zip')) as archive:
                for name in ('rx.ci8','capture.json'):
                    with archive.open(prefix+'/'+name) as src, (capture_dir/name).open('xb') as dest:
                        while block:=src.read(1_048_576):
                            dest.write(block)
            path=capture_dir/'rx.ci8'
        for name in ('rx.ci8','capture.json'):
            if digest(capture_dir/name)!=evidence['files'][prefix+'/'+name]:
                raise ValueError('Özgün RF girdi özeti eşleşmiyor.')
        capture=json.loads((capture_dir/'capture.json').read_text(encoding='utf-8'))
        raw=np.memmap(path,dtype=np.int8,mode='r').reshape(-1,2)
        context={'sample_rate_hz':8_000_000,'center_frequency_hz':825_300_000,
            'lower_frequency_hz':824_989_819.3359375-width/2,
            'upper_frequency_hz':824_989_819.3359375+width/2}
        rows=[]
        for at in [1.]+[start+i*.4 for i in range(10)]:
            first=round(at*8_000_000)
            codes=raw[first:first+2_000_000].astype(float)
            if np.any((codes==-128)|(codes==127)):
                raise ValueError('Seçilen gerçek I/Q penceresinde kırpılma var.')
            x=(codes[:,0]+1j*codes[:,1])/128
            result=observe_rf(x,**context)
            rows.append({'start_s':at,'role':'pre' if at==1. else 'on','result':result.to_dict()})
            if label=='AM_new' and at==start:
                scaled=observe_rf(x*2,**context)
                shifted_context={key:value+(100_000_000 if key!='sample_rate_hz' else 0)
                                 for key,value in context.items()}
                shifted=observe_rf(x,**shifted_context)
                power_error=abs(scaled.signal_power_dbfs-result.signal_power_dbfs-20*np.log10(2))
                snr_error=abs(scaled.snr_db-result.snr_db)
                feature_error=max(abs(scaled.features[k]-result.features[k]) for k in result.features)
                frequency_error=abs(shifted.spectral_center_hz-result.spectral_center_hz-100_000_000)
                if power_error>1e-8 or snr_error>1e-8 or feature_error>1e-8 or frequency_error>1e-5:
                    raise ValueError('Gerçek I/Q ölçek/frekans bağlamı kontrolü başarısız.')
                report['checks']['real_iq_scale_and_frequency']={
                    'power_error_db':float(power_error),'snr_error_db':float(snr_error),
                    'feature_max_absolute_change':float(feature_error),
                    'absolute_frequency_context_error_hz':float(frequency_error)}
                try:
                    observe_rf(x,**{**context,'lower_frequency_hz':825_295_000,'upper_frequency_hz':825_305_000})
                except ValueError:
                    report['checks']['receiver_dc_band_rejected']=True
                else:
                    raise ValueError('Alıcı DC aralığı reddedilmedi.')
        case={'label_for_reporting_only':label,'evidence':evidence_path.relative_to(ROOT).as_posix(),
            'evidence_sha256':digest(evidence_path),'raw_sha256':capture['raw_sha256'],
            'transport_valid':capture['transport_valid'],'usb_overruns':capture['usb_overruns'],
            'independent_rf_captures':1,'selected_span_hz':width,'rows':rows}
        report['cases'].append(case)
        print(json.dumps({'label':label,'quality_pass':sum(r['result']['quality_reason'] is None for r in rows[1:]),
            'windows':10,'transport_valid':capture['transport_valid']},ensure_ascii=False),flush=True)
        del raw
    report['checks']['no_unvalidated_definite_classes']=all(r['result']['signal_domain']=='Belirsiz'
        for c in report['cases'] for r in c['rows'])
    report['checks']['low_snr_does_not_erase_power']=all(r['result']['signal_power_dbfs'] is not None
        for c in report['cases'] for r in c['rows'] if r['result']['quality_reason']=='low_snr' and r['result']['snr_db'] is not None)
    if not all(v for v in report['checks'].values()):
        raise ValueError('Alan bağımsızlığı kontrolü başarısız.')
    with (output/'report.json').open('x',encoding='utf-8') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--captures-root',type=Path,default=Path(os.environ['TEMP']))
    args=parser.parse_args()
    evaluate(args.output,args.captures_root)
