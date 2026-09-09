import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import dataresearch as d
from restore_dataresearch import restore

class Response(io.BytesIO):
    def __init__(self,data,ct='text/html',url=d.BASE+'/test'):
        super().__init__(data);self.headers={'Content-Type':ct};self.url=url

class ArchiveTests(unittest.TestCase):
    def test_query_variants_and_relative_links(self):
        self.assertEqual(d.canonical('../file.csv?page=2&utm_source=x#top',d.BASE+'/a/b'),d.BASE+'/file.csv?page=2')
        self.assertNotEqual(d.canonical('?page=1',d.BASE),d.canonical('?page=2',d.BASE))
    def test_discovery_and_scope(self):
        links,embeds=d.discover(b'<a href="next?page=2">Next</a><a href="https://www.ndis.gov.au/a.xlsx">Data</a><iframe src="https://app.powerbi.com/view?r=abc"></iframe>',d.BASE+'/datasets/','text/html')
        self.assertIn(d.BASE+'/datasets/next?page=2',links)
        self.assertTrue(d.in_scope('https://www.ndis.gov.au/a.xlsx'))
        self.assertFalse(d.in_scope('https://www.ndis.gov.au/participants'))
        self.assertIn('https://app.powerbi.com/view?r=abc',embeds)
    def test_chunks_are_lossless_and_unchanged_has_no_event(self):
        with tempfile.TemporaryDirectory() as t, patch.object(d,'CHUNK',4):
            c=d.Crawler(Path(t),delay=0);u=d.BASE+'/file.csv';data=b'abcdefghijk'
            c.response=lambda u:Response(data,'text/csv',u)
            c.capture(u)
            e=c.entries[u]
            self.assertEqual(b''.join((Path(t)/e['directory']/p).read_bytes() for p in e['files']),data)
            self.assertEqual(len(e['files']),3)
            c.capture(u);self.assertEqual(len(c.events),1)
    def test_restore_and_hash_failure(self):
        with tempfile.TemporaryDirectory() as t, patch.object(d,'CHUNK',4):
            c=d.Crawler(Path(t)/'archive',delay=0);u=d.BASE+'/data.zip'
            c.response=lambda u:Response(b'123456789','application/zip',u);c.capture(u)
            meta=c.archive/c.entries[u]['directory']/'metadata.json';out=Path(t)/'data.zip'
            restore(meta,out);self.assertEqual(out.read_bytes(),b'123456789')
            with self.assertRaises(FileExistsError):restore(meta,out)
            (meta.parent/c.entries[u]['files'][0]).write_bytes(b'bad')
            broken=Path(t)/'bad.zip'
            with self.assertRaises(ValueError):restore(meta,broken)
            self.assertFalse(broken.exists())
    def test_file_html_error_preserves_previous(self):
        with tempfile.TemporaryDirectory() as t:
            c=d.Crawler(Path(t),delay=0);u=d.BASE+'/file.csv'
            c.response=lambda u:Response(b'original','text/csv',u);c.capture(u)
            old=dict(c.entries[u]);c.response=lambda u:Response(b'<html>error</html>','text/html',u)
            with self.assertRaises(RuntimeError):c.capture(u)
            self.assertEqual(c.entries[u],old)
            self.assertEqual((Path(t)/old['directory']/old['files'][0]).read_bytes(),b'original')
    def test_failure_saved_and_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as t:
            c=d.Crawler(Path(t),delay=0)
            c.capture=lambda u:(_ for _ in ()).throw(RuntimeError('blocked'))
            self.assertEqual(c.run(),1)
            self.assertEqual(c.manifest['status'],'partial')
            self.assertTrue((Path(t)/'latest-run.json').exists())
    def test_bounded_run_keeps_pending_inventory(self):
        with tempfile.TemporaryDirectory() as t:
            c=d.Crawler(Path(t),max_urls=0,delay=0)
            self.assertEqual(c.run(),1)
            self.assertEqual(len(c.manifest['pending']),2)
    def test_checkpoint_does_not_duplicate_ledger(self):
        with tempfile.TemporaryDirectory() as t:
            c=d.Crawler(Path(t),delay=0)
            c.response=lambda u:Response(b'<main>First</main>');c.capture(d.BASE+'/test')
            c.save();c.save()
            self.assertEqual(len((Path(t)/'change-log.csv').read_text().splitlines()),2)

if __name__=='__main__':unittest.main()
