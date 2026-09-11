"""Build isolated ARM service/bridge binaries for the runtime-control image."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
from build_st06_weak_service import SOURCES, INCLUDES

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'build/p0/st06-runtime-config-v2-20260910/software'


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    prefix=['wsl.exe'] if os.name=='nt' else []
    flags=['-std=c11','-O3','-mcpu=cortex-a9','-mfpu=neon','-mfloat-abi=hard',
           '-Wall','-Wextra','-Werror','-pedantic']
    products={'p0-ed-service': SOURCES,
              'p0-ed-network-bridge': [f'platforms/embedded/p0/src/{name}.c' for name in
                                      ('p0_ed_network_bridge','p0_ed_service_protocol','p0_iq_transport')]}
    binaries={}
    for name, sources in products.items():
        target=(OUTPUT/name).relative_to(ROOT).as_posix()
        subprocess.run([*prefix,'arm-linux-gnueabihf-gcc',*flags,*(f'-I{p}' for p in INCLUDES),
                        *sources,'-lm','-pthread','-o',target],cwd=ROOT,check=True)
        binaries[name]={'path':target,'sha256':hashlib.sha256((ROOT/target).read_bytes()).hexdigest()}
    all_files=set(p for sources in products.values() for p in sources)
    all_files.update(p.relative_to(ROOT).as_posix() for folder in INCLUDES for p in (ROOT/folder).glob('*.h'))
    all_files.add('scripts/build_st06_runtime_services.py')
    result={'status':'compiled','hardware_executed':False,'flags':flags,'binaries':binaries,
            'sources':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(all_files)}}
    (OUTPUT/'build.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    result=build()
    print(json.dumps({'status':result['status'],'binaries':result['binaries']},indent=2))
