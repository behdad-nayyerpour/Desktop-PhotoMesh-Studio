"""Replay actual native timestamps through the shared observed-work ETA meter."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys


def validate(log, output):
    from photomesh.progress import WorkProgress
    current = [0.]
    meter = WorkProgress(clock=lambda:current[0])
    samples = []
    pattern = re.compile(r'^I(\d{8} \d{2}:\d{2}:\d{2}\.\d+).*Processed file \[(\d+)/(\d+)\]')
    start = None
    for line in log.read_text(encoding='utf-8').splitlines():
        match = pattern.search(line)
        if not match:
            continue
        stamp, done, total = match.groups()
        stamp = datetime.strptime(stamp,'%Y%m%d %H:%M:%S.%f').timestamp()
        start = stamp if start is None else start
        current[0] = stamp-start
        done, total = int(done), int(total)
        meter.update(done, total)
        samples.append(dict(seconds=current[0],done=done,total=total,eta=meter.remaining()))
    assert len(samples) > 3 and samples[-1]['done'] == samples[-1]['total']
    assert all(a['done'] < b['done'] and a['seconds'] <= b['seconds'] for a,b in zip(samples,samples[1:]))
    end = samples[-1]['seconds']
    errors = [dict(at=s['done'],estimated=s['eta'],actual=end-s['seconds'],absolute_error=abs(s['eta']-(end-s['seconds'])))
              for s in samples if s['eta'] is not None and s['done'] < s['total']]
    record = dict(operation='CPU feature extraction, actual public survey native log timestamps',
                  counted_images=samples[-1]['total'],seconds_since_first_completed_image=end,
                  eta_samples=len(errors),eta_errors=errors,samples=samples,
                  limitation='One CPU extraction workload; short/bursty rates are intentionally suppressed, no GPU/cached-work claim')
    output.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ('samples','eta_errors')},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    validate(args.log,args.output)
