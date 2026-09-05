"""Kaynak bağlı ST-06 paralel ARM ürün kanıtı; RF/soğuk açılış kabulü değildir."""
from pathlib import Path
import argparse,hashlib,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.operator_console.live_ed import decode_live_ed_response
from scripts.verify_phase08_evidence_recovery import verify_frozen_file
EVIDENCE=ROOT/'results/evidence/phase08/st06-parallel-product-v1.json'
def verify(*, historical=False):
 for name in ('st06-parallel-product-v1.json','st06-parallel-product-v1.zip'):
  verify_frozen_file('results/evidence/phase08/'+name,root=ROOT)
 r=json.loads(EVIDENCE.read_text(encoding='utf-8'))
 archive=ROOT/r['archive']['path']
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==r['archive']['sha256']
 if not historical:
  for name,digest in r['source_sha256'].items():
   assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest, 'Güncel kaynak kanıtla eşleşmiyor: '+name
 for artifact in r['artifacts'].values():
  assert hashlib.sha256((ROOT/artifact['path']).read_bytes()).hexdigest()==artifact['sha256']
 baseline=json.loads((ROOT/'results/evidence/phase08/st06-product-optimization-v1.json').read_text(encoding='utf-8'))['physical_runs'][0]['cases']
 with zipfile.ZipFile(archive) as z:
  for name,digest in r['source_sha256'].items():
   assert hashlib.sha256(z.read('current-sources/'+name)).hexdigest()==digest
  assert hashlib.sha256(z.read('package/p0-ed-service')).hexdigest()==r['service_sha256']
  assert z.read('package/board-metadata.txt').decode().split()[0]==r['service_sha256']
  for i,run in enumerate(r['physical_runs'],1):
   assert run['script_sha256']==r['source_sha256']['scripts/diagnose_st06_product_board.py']
   for name,c in run['cases'].items():
    assert all(c['transport'][key]==0 for key in ['crc_errors','sequence_errors','queue_drops'])
    assert c['input_sha256']==baseline[name]['input_sha256']
    assert c['response_sha256']==baseline[name]['response_sha256']
    raw=z.read(f'physical-{i}/{name}.responses.bin');stim=z.read(f'physical-{i}/{name}.ci8')
    assert hashlib.sha256(raw).hexdigest()==c['response_sha256']
    assert hashlib.sha256(stim).hexdigest()==c['input_sha256']
    count=0;offset=0;last=None
    while offset<len(raw):
     size=int.from_bytes(raw[offset:offset+4],'little');offset+=4
     assert 68<=size<=16384
     last=decode_live_ed_response(raw[offset:offset+size],count);offset+=size;count+=1
     assert last.dma_status_flags==7 and last.dropped_candidates==0
    assert offset==len(raw) and count==c['received_frames'] and not last.active
    assert len(stim)==count*8192
    times=json.loads(z.read(f'physical-{i}/{name}.arrival-times.json'))
    assert len(times)==count and all(y>=x for x,y in zip(times,times[1:]))
    if name=='repeated_tone_throughput':
     assert 4096/(times[4159]-times[63])==c['measured_fps_after_64_warmup']
  soak=r['soak'];raw=z.read('soak/responses.bin');stim=z.read('soak/input.ci8')
  assert hashlib.sha256(raw).hexdigest()==soak['response_sha256']
  assert hashlib.sha256(stim).hexdigest()==soak['input_sha256']
  offset=0;count=0
  while offset<len(raw):
   size=int.from_bytes(raw[offset:offset+4],'little');offset+=4
   assert 68<=size<=16384
   last=decode_live_ed_response(raw[offset:offset+size],count);offset+=size;count+=1
   assert last.dma_status_flags==7 and last.dropped_candidates==0
  assert count==16080 and offset==len(raw) and not last.active
  assert len(stim)==count*8192
  times=json.loads(z.read('soak/arrival-times.json'))
  assert len(times)==count and 16000/(times[16063]-times[63])==soak['fps']
  assert 'Successfully built p0-dma' in z.read('package/package-build.txt').decode()
  assert 'Successfully built project' in z.read('package/image-build.txt').decode()
  host=json.loads(z.read('validation/host.json'));assert host['status']=='passed'
  san=json.loads(z.read('validation/sanitizer.json'));assert san['status']=='passed'
  stream=json.loads(z.read('validation/stream.json'));assert stream['status']=='passed' and stream['stream_mismatches']==0
  for name,digest in stream['source_sha256'].items():
   if historical and 'current-sources/'+name in z.namelist():
    assert hashlib.sha256(z.read('current-sources/'+name)).hexdigest()==digest,name
   else:
    # Bazı ek doğrulama kaynakları eski arşivde yoktur. Yalnız aynı
    # baytlar mevcutsa doğrulanabilir; değişmiş kaynak kabul edilmez.
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
 speeds=[run['cases']['repeated_tone_throughput']['measured_fps_after_64_warmup'] for run in r['physical_runs']]
 assert speeds==r['fps'] and len(speeds)==3
 assert min(speeds)>=2000000/4096 and soak['fps']>=2000000/4096
 assert r['gates']['digital_product_throughput'] is True
 assert r['gates']['RF_acceptance'] is False and r['gates']['cold_boot'] is False and r['gates']['ST06_complete'] is False
 return r
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--historical',action='store_true',help='Yalnız özgün arşivi denetle; güncel kaynak kabulü değildir.')
 args=parser.parse_args()
 r=verify(historical=args.historical)
 print(json.dumps({'integrity':'passed','scope':'historical_record' if args.historical else 'current_source_bound_record','fps':r['fps'],'soak_fps':r['soak']['fps'],'ST06_complete':False}))
