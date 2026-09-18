import sys, os, json, hashlib, tempfile, subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from app.operator_console.measurement_record import read_measurement
from algorithms.spectrum import SpectrumProcessor
from algorithms.parameters.extended_center import extended_center_reference
from algorithms.parameters.extended_obw import extended_obw_reference
from verify_p0_parameter_runtime import _build, _ci8

record=Path(os.environ['LOCALAPPDATA'])/'TEKNOFEST 2026 Elektronik Harp'/'BÂZ'/'parameter-records'/sys.argv[1]
doc,frames=read_measurement(record)
lo=doc['intent']['span']['lower_shifted_bin'];hi=doc['intent']['span']['upper_shifted_bin']
fs=doc['sample_rate_hz'];center=doc['center_frequency_hz']
with tempfile.TemporaryDirectory() as raw:
    folder=Path(raw);exe,_,compiler=_build(folder);paths=[];psd=[]
    for i,frame in enumerate(frames):
        iq,decoded=_ci8(frame)
        spectrum=SpectrumProcessor().process(decoded,sample_rate_hz=fs,center_frequency_hz=center)
        power=np.rint(np.asarray(spectrum.fft_power_unshifted)*(1<<30)).astype('<u8')
        psd.append(np.fft.fftshift(power.astype(float))/(1<<30)/(fs*1536))
        ip,pp=folder/f'{i}.iq',folder/f'{i}.power';ip.write_bytes(iq);pp.write_bytes(power.tobytes());paths.extend((ip,pp))
    result_path=folder/'result.json'
    subprocess.run([str(exe),str(int(fs)),str(int(center)),str(lo),str(hi),*map(str,paths),str(result_path)],check=True,capture_output=True)
    result=json.loads(result_path.read_text())
    report={'record':record.name,'record_sha256':hashlib.sha256(record.read_bytes()).hexdigest(),
            'compiler':compiler,'original_fields':doc['fields'],'original_quality':doc['quality'],
            'portable_c_result':result,'physical_replay':False,
            'center_reference':extended_center_reference(frames,lo,hi) if len(frames)==16 else None,
            'obw_reference':extended_obw_reference(psd,lo,hi) if len(frames)==16 else None}
    Path(sys.argv[2]).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('emission_center_frequency_hz','occupied_bandwidth_hz','quality')}))
