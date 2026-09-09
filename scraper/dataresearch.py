#!/usr/bin/env python3
"""Archive discoverable dataresearch pages/files and report gaps explicitly."""
from __future__ import annotations
import argparse
import csv
import difflib
import hashlib
import json
import re
import sys
import time
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'project'))
from gov_tracker import USER_AGENT, visible_lines
HOST = 'dataresearch.ndis.gov.au'
BASE = 'https://' + HOST
FILES = {'.pdf','.doc','.docx','.xls','.xlsx','.csv','.tsv','.zip','.rtf','.txt','.ppt','.pptx','.json','.xml','.ods','.odt','.mp3','.mp4','.webm','.wav'}
ASSETS = {'.css','.js','.png','.jpg','.jpeg','.gif','.svg','.webp','.ico','.woff','.woff2','.ttf'}
CHUNK = 25 * 1024 * 1024


def stamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def canonical(link, base):
    p = urlsplit(urljoin(base, link))
    if p.scheme not in {'http','https'} or not p.hostname or p.username or p.password:
        return None
    query = [(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid'}]
    return urlunsplit((p.scheme, p.netloc.lower(), p.path or '/', urlencode(sorted(query)), ''))


class Links(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.links, self.embeds = base, set(), set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'base' and a.get('href'):
            self.base = urljoin(self.base,a['href'])
        for key in ('href','src','data','poster'):
            if a.get(key):
                u = canonical(a[key],self.base)
                if u:
                    self.links.add(u)
                    if tag in {'iframe','embed','object'}: self.embeds.add(u)
        for part in a.get('srcset','').split(','):
            if part.strip():
                u = canonical(part.strip().split()[0],self.base)
                if u: self.links.add(u)


def discover(data, url, content_type):
    parser = Links(url)
    text = data.decode('utf-8',errors='replace')
    if 'html' in content_type:
        parser.feed(text)
    elif 'css' in content_type:
        for link in re.findall(r'url\(\s*[\'"]?([^\)\'"\s]+)',text):
            u = canonical(link,url)
            if u: parser.links.add(u)
    elif 'xml' in content_type:
        import xml.etree.ElementTree as ET
        try:
            tree = ET.fromstring(data)
            for node in tree.iter():
                if node.tag.split('}')[-1] == 'loc' and node.text:
                    u=canonical(node.text.strip(),url)
                    if u:parser.links.add(u)
        except ET.ParseError: pass
    return parser.links, parser.embeds


def in_scope(url):
    p=urlsplit(url)
    # Crawl all public pages on this site; follow linked publications on other hosts.
    return p.hostname == HOST or Path(p.path).suffix.lower() in FILES


def write_json(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
    temp.replace(path)


class Crawler:
    def __init__(self, archive, max_seconds=4200, max_urls=20000, delay=.5):
        self.archive=archive
        self.archive.mkdir(parents=True,exist_ok=True)
        p=archive/'manifest.json'
        self.manifest=json.loads(p.read_text()) if p.exists() else {'format_version':1,'entries':{}}
        self.entries=self.manifest['entries']
        self.checked=stamp(); self.started=time.monotonic()
        self.max_seconds=max_seconds; self.max_urls=max_urls; self.delay=delay
        self.robots={}; self.errors=[]; self.skipped={}; self.external={}; self.events=[]
        self.attempted=set(); self.queue=deque(); self.queued=set()
        self.pending=[]; self.captured=0
    def enqueue(self,url):
        if url not in self.queued:
            self.queued.add(url);self.queue.append(url)
    def request(self,url):
        time.sleep(self.delay)
        return urlopen(Request(url,headers={'User-Agent':USER_AGENT,'Accept':'*/*'}),timeout=45)
    def allowed(self,url):
        p=urlsplit(url); origin=urlunsplit((p.scheme,p.netloc,'','',''))
        if origin not in self.robots:
            parser=RobotFileParser(origin+'/robots.txt')
            try:
                with self.request(origin+'/robots.txt') as r: rules=r.read().decode('utf-8',errors='replace')
                parser.parse(rules.splitlines())
            except HTTPError as e:
                if e.code==404: parser.parse([])
                else: raise RuntimeError(f'robots.txt unavailable ({e.code}) for {origin}') from e
            self.robots[origin]=parser
        return self.robots[origin].can_fetch(USER_AGENT,url)
    def response(self,url):
        # Check every redirect target's robots before requesting it.
        from urllib.request import build_opener, HTTPRedirectHandler
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):return None
        opener=build_opener(NoRedirect())
        for _ in range(10):
            if not self.allowed(url):raise PermissionError('Disallowed by robots.txt: '+url)
            time.sleep(self.delay)
            try:return opener.open(Request(url,headers={'User-Agent':USER_AGENT,'Accept':'*/*'}),timeout=45)
            except HTTPError as e:
                if e.code in {301,302,303,307,308} and e.headers.get('Location'):
                    target=canonical(e.headers['Location'],url)
                    if not target:raise RuntimeError('Unsupported redirect')
                    url=target
                else:raise
        raise RuntimeError('Too many redirects')
    def event(self,url,old,new,old_data,new_data):
        event='new' if not old else 'restored' if old.get('status')=='missing' else 'changed'
        record={'checked_at':self.checked,'event':event,'url':url,'previous_hash':(old or {}).get('sha256',''),'new_hash':new['sha256'],'kind':new['kind']}
        self.events.append(record)
        folder=self.archive/new['directory']; history=folder/'changelog.md'
        with history.open('a') as f:
            if history.stat().st_size==0:f.write(f'# Resource history\n\nSource: {url}\n')
            f.write(f'\n## {self.checked} — {event}\n\nSHA-256: `{new["sha256"]}`\n')
            if old and new['kind']=='page':
                diff=list(difflib.unified_diff(visible_lines(old_data),visible_lines(new_data),fromfile='before',tofile='after',lineterm=''))
                f.write('\n```diff\n'+'\n'.join(diff)+'\n```\n' if diff else '\nNo visible wording change; HTML bytes changed.\n')
    def capture(self,url):
        old=self.entries.get(url)
        with self.response(url) as r:
            final=canonical(r.url,url); ct=r.headers.get('Content-Type','').lower()
            if 'html' in ct and Path(urlsplit(url).path).suffix.lower() in FILES:
                raise RuntimeError('Expected a downloadable file but received HTML; previous capture retained')
            kind='page' if 'html' in ct else 'file'
            directory='resources/'+hashlib.sha256(url.encode()).hexdigest()
            folder=self.archive/directory;folder.mkdir(parents=True,exist_ok=True)
            # Stage chunks before replacing a verified capture; no Git blob exceeds 25 MiB.
            digest=hashlib.sha256(); size=0; paths=[]; preview=bytearray()
            try:
                while True:
                    data=r.read(CHUNK)
                    if not data:break
                    digest.update(data);size+=len(data)
                    p=folder/f'.incoming-{len(paths):05d}';p.write_bytes(data);paths.append(p)
                    if len(preview)<10*1024*1024:preview.extend(data[:10*1024*1024-len(preview)])
            except Exception:
                for p in paths:p.unlink(missing_ok=True)
                raise
            if not size:raise RuntimeError('Empty response; previous capture retained')
            text=bytes(preview)
            if kind=='page' and size>len(preview):raise RuntimeError('HTML exceeds parser limit; capture needs review')
            links,embeds=discover(text,final,ct)
            for u in sorted(links):
                if in_scope(u):self.enqueue(u)
                else:self.external.setdefault(u,set()).add(url)
            for u in embeds:self.external.setdefault(u,set()).add(url)
            names=['index.html'] if kind=='page' else ['content.bin'] if len(paths)==1 else [f'content.part-{i:05d}' for i in range(len(paths))]
            new={'url':url,'final_url':final,'sha256':digest.hexdigest(),'bytes':size,'response_headers':{k:r.headers.get(k) for k in ('Content-Disposition','Last-Modified','ETag') if r.headers.get(k)},'kind':kind,'content_type':ct,'directory':directory,'files':names,'links':sorted(links),'embeds':sorted(embeds),'status':'active','first_seen':(old or {}).get('first_seen',self.checked),'last_changed':(old or {}).get('last_changed',self.checked)}
            changed=not old or old['sha256']!=new['sha256'] or old.get('status')!='active' or any(not (self.archive/old['directory']/name).exists() for name in old['files'])
            if changed:
                old_data=b''
                if old and old.get('kind')=='page':
                    old_path=self.archive/old['directory']/old['files'][0]
                    if old_path.exists():old_data=old_path.read_bytes()
                for p,name in zip(paths,names):p.replace(folder/name)
                if old:
                    for name in old['files']:
                        if name not in names:(folder/name).unlink(missing_ok=True)
                new['last_changed']=self.checked
                self.event(url,old,new,old_data,text)
            else:
                for p in paths:p.unlink(missing_ok=True)
            self.entries[url]=new;self.captured+=1
            write_json(folder/'metadata.json',new)
            print(f'{"UPDATED" if changed else "UNCHANGED"} {size} {url}',flush=True)
    def run(self):
        # Prior incomplete inventory is processed first so bounded runs make progress.
        for u in self.manifest.get('pending',[]):self.enqueue(u)
        self.enqueue(BASE+'/sitemap');self.enqueue(BASE+'/')
        for u in self.entries:self.enqueue(u)
        while self.queue:
            if time.monotonic()-self.started>self.max_seconds or len(self.attempted)>=self.max_urls:break
            url=self.queue.popleft();self.attempted.add(url)
            try:self.capture(url)
            except PermissionError as e:self.skipped[url]=str(e)
            except (HTTPError,URLError,TimeoutError,OSError,ValueError,RuntimeError) as e:
                self.errors.append({'url':url,'error':str(e)})
                print(f'ERROR {url}: {e}',flush=True)
                # Preserve known outgoing links if this page cannot be refreshed.
                for link in self.entries.get(url,{}).get('links',[]):
                    if in_scope(link):self.enqueue(link)
            if len(self.attempted)%20==0:self.save()
        self.save()
        return 1 if self.errors or self.queue else 0
    def save(self):
        pending=list(self.queue)
        status='partial' if self.errors or pending else 'complete-with-exclusions' if self.skipped else 'complete'
        self.manifest.update(checked_at=self.checked,status=status,pending=pending)
        write_json(self.archive/'manifest.json',self.manifest)
        report={'checked_at':self.checked,'status':status,'attempted':len(self.attempted),'captured':self.captured,'pending':len(pending),'errors':self.errors,'robots_exclusions':self.skipped,'external_links_and_embeds':{k:sorted(v) for k,v in sorted(self.external.items())},'events':self.events}
        write_json(self.archive/'latest-run.json',report)
        write_json(self.archive/'runs'/(self.checked.replace(':','')+'.json'),report)
        # Replace this run's report at checkpoints; append events only once at final export.
        lines=['# Data and research archive',f'\nLast checked: {self.checked}',f'\nStatus: **{status}**',f'\nCaptured this run: {self.captured}; pending: {len(pending)}; errors: {len(self.errors)}; robots exclusions: {len(self.skipped)}.', '\n[Manifest](manifest.json) · [Run details and external embeds](latest-run.json)','\n## Captured resources\n']
        for url,e in sorted(self.entries.items()):lines.append(f'- [{url}]({e["directory"]}/metadata.json) — {e["kind"]}, {e["bytes"]} bytes')
        (self.archive/'README.md').write_text('\n'.join(lines)+'\n')
        ledger=self.archive/'change-log.csv'
        fields=['checked_at','event','url','previous_hash','new_hash','kind']
        rows=[]
        if ledger.exists():
            with ledger.open() as handle: rows=list(csv.DictReader(handle))
        rows=[r for r in rows if r['checked_at']!=self.checked]+self.events
        with ledger.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive-root',type=Path,default=ROOT/'archive/dataresearch')
    p.add_argument('--max-seconds',type=int,default=4200)
    p.add_argument('--max-urls',type=int,default=20000)
    args=p.parse_args()
    return Crawler(args.archive_root,args.max_seconds,args.max_urls).run()

if __name__=='__main__':raise SystemExit(main())
