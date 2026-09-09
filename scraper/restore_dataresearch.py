#!/usr/bin/env python3
"""Restore one captured resource, verifying its SHA-256 before saving the output."""
import argparse
import hashlib
import json
from pathlib import Path


def restore(metadata_path, destination):
    metadata=json.loads(metadata_path.read_text())
    if destination.exists():raise FileExistsError(f'Output already exists: {destination}')
    digest=hashlib.sha256();size=0
    # Exclusive creation protects existing originals; delete only our incomplete output.
    with destination.open('xb') as output:
        try:
            for name in metadata['files']:
                if Path(name).name!=name:raise ValueError('Invalid chunk filename')
                with (metadata_path.parent/name).open('rb') as source:
                    while data:=source.read(1024*1024):
                        output.write(data);digest.update(data);size+=len(data)
            if digest.hexdigest()!=metadata['sha256'] or size!=metadata['bytes']:
                raise ValueError('Archive integrity check failed')
        except Exception:
            output.close();destination.unlink();raise
    return destination

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('metadata',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(restore(a.metadata,a.output))
