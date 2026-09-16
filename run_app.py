"""Portal evaluasi foto isolator. Jalankan: python run_app.py

Python 3.10+; server memakai standard library. Excel tersimpan di outputs/portal.
Pembuatan ulang Excel memakai runtime Node + Artifact Tool yang tersedia di komputer.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
from datetime import datetime
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import threading
from urllib.parse import parse_qs, unquote, urlsplit
import webbrowser
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
WORK = ROOT / 'outputs/portal_work'
OUTPUT = ROOT / 'outputs/portal'
ASSETS = ROOT / 'portal_assets'
EXCEL = OUTPUT / 'Ringkasan_Eksekutif_Lapis_1_2_3.xlsx'
FEATURES = ['ragu2','cakupan_foto','jumlah_renteng_terbaca','arah_isolator','bahan_isolator','cahaya','ketajaman','noise','halangan','isi_frame_terbanyak','bagian_renteng_terlihat']
LABELS = ['Ragu (sesuai atau jauh)','Cakupan foto','Renteng terbaca','Arah isolator','Bahan isolator','Cahaya','Ketajaman','Noise','Halangan','Isi frame terbanyak','Bagian renteng terlihat']
FILES = {
 'l1': ROOT/'outputs/lapis1_work/hasil_lapis1.csv',
 'l2': ROOT/'outputs/lapis2_work/hasil_lapis2.csv',
 'clusters': ROOT/'outputs/lapis3_work/clusters.csv',
 'members': ROOT/'outputs/lapis3_work/cluster_members.csv',
 'pairs': ROOT/'outputs/lapis3_work/pair_relationships.csv',
 'index': ROOT/'outputs/lapis3_work/image_index.csv',
}
DASHBOARDS = {
 '1': 'outputs/lapis1_20260912_01a095d1/Dashboard_Evaluasi_Lapis_1_Foto_Isolator.html',
 '2': 'outputs/lapis2_20260913/Dashboard_Evaluasi_Lapis_2_Foto_Isolator.html',
}
BOOKS = {
 '1':'outputs/lapis1_20260912_01a095d1/Hasil_Evaluasi_Lapis_1_Foto_Isolator.xlsx',
 '2':'outputs/lapis2_20260913/Hasil_Evaluasi_Lapis_2_Foto_Isolator.xlsx',
 '3':'outputs/lapis3_20260913/Hasil_Evaluasi_Lapis_3_Relasi_Duplikasi_Foto_Isolator.xlsx',
}
PHOTO_DIRS = {'ULTG LOMBOK BARAT','ULTG LOMBOK TIMUR','ULTG SUMBAWA'}

def read_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as handle:
        yield from csv.DictReader(handle)

def number(v):
    return float(v) if v not in ('',None) else None

def signature():
    paths = list(FILES.values())+[Path(__file__),ASSETS/'build_executive.mjs']
    return hashlib.sha256(json.dumps([(str(p.relative_to(ROOT)),p.stat().st_size,p.stat().st_mtime_ns) for p in paths]).encode()).hexdigest()

def file_hash(p):
    with p.open('rb') as h:
        return hashlib.file_digest(h,'sha256').hexdigest() if hasattr(hashlib,'file_digest') else hashlib.sha256(h.read()).hexdigest()

class Dataset:
    def __init__(self):
        for p in [*FILES.values(),*(ROOT/x for x in DASHBOARDS.values()),*(ROOT/x for x in BOOKS.values())]:
            if not p.is_file(): raise FileNotFoundError(f'File sumber belum tersedia: {p}')
        WORK.mkdir(parents=True,exist_ok=True);OUTPUT.mkdir(parents=True,exist_ok=True)
        self.signature=signature()
        l1=list(read_csv(FILES['l1'])); l2=list(read_csv(FILES['l2']))
        keys={r['path_rel']:r for r in l1}
        assert len(keys)==len(l1), 'Kunci foto Lapis 1 ganda'
        assert len({r['path_rel'] for r in l2})==len(l2), 'Kunci foto Lapis 2 ganda'
        assert all(r['path_rel'] in keys and r['kode']==keys[r['path_rel']]['kode'] for r in l2), 'Kode Lapis 1 dan Lapis 2 berbeda'
        self.members=defaultdict(list)
        for r in read_csv(FILES['members']):
            r['quality_score']=number(r['quality_score']); self.members[r['duplicate_group_id']].append(r)
        self.clusters=[]
        for r in read_csv(FILES['clusters']):
            for k in ['average_similarity','minimum_similarity','strong_edge_ratio','cluster_diameter']: r[k]=number(r[k])
            r['jumlah_gambar']=int(r['jumlah_gambar']); r.pop('member_images',None)
            ms=self.members[r['duplicate_group_id']]
            assert len(ms)==r['jumlah_gambar'], 'Jumlah anggota cluster berbeda'
            r['ultg']='; '.join(sorted({m['ultg'] for m in ms}))
            r['kode_l1_canonical']=keys[r['canonical_image']]['kode']
            self.clusters.append(r)
        self.cluster_by_id={r['duplicate_group_id']:r for r in self.clusters}
        self.db=WORK/'relationships.sqlite3'
        self.prepare_pairs(keys)
        with closing(sqlite3.connect(self.db)) as db:
            pair_count=db.execute('select count(*) from pairs').fetchone()[0]
            types=dict(db.execute('select relationship_type,count(*) from pairs group by relationship_type'))
            confidence=dict(db.execute('select duplicate_confidence,count(*) from pairs group by duplicate_confidence'))
        n_index=sum(1 for _ in read_csv(FILES['index']))
        self.summary={
          'updated':datetime.fromtimestamp(max(p.stat().st_mtime for p in FILES.values())).astimezone().isoformat(timespec='seconds'),
          'l1':{'total':len(l1),'codes':dict(Counter(r['kode'] for r in l1)),'review':sum(r['perlu_review_manual']=='YA' for r in l1),'by_ultg':{}},
          'l2':{'total':len(l2),'sample':sum(r['sampel_audit_1500']=='YA' for r in l2),'with_gaps':sum(int(r['jumlah_belum_dinilai'])>0 for r in l2),'gap_cells':sum(int(r['jumlah_belum_dinilai']) for r in l2),'features':[]},
          'l3':{'images':n_index,'pairs':pair_count,'clusters':len(self.clusters),'members':sum(len(x) for x in self.members.values()),'statuses':dict(Counter(r['cluster_status'] for r in self.clusters)),'types':types,'confidence':confidence},
        }
        for u in sorted({r['ultg'] for r in l1}):
            rs=[r for r in l1 if r['ultg']==u];self.summary['l1']['by_ultg'][u]={'total':len(rs),'sesuai':sum(r['kode']=='S' for r in rs)}
        for f,label in zip(FEATURES,LABELS):
            counts=dict(Counter(r[f] for r in l2));self.summary['l2']['features'].append({'field':f,'label':label,'counts':counts})
        assert n_index==len(l2), 'Cakupan Lapis 3 berbeda dari Lapis 2 aktif'
        # A four-sheet analytical workbook: L3 uses one row per cluster member.
        l1_fields=['ultg','nama_file','kode','nama_keputusan','confidence','perlu_review_manual','alasan','lebar','tinggi','ukuran_byte','status_baca']
        l2_fields=['ultg','nama_file','kode','sampel_audit_1500',*FEATURES,'jumlah_belum_dinilai','validasi_manual_lapis2','catatan_reviewer']
        l3_rows=[]
        for c in self.clusters:
            for m in self.members[c['duplicate_group_id']]:
                l3_rows.append([c['duplicate_group_id'],c['cluster_status'],c['jumlah_gambar'],c['cluster_confidence'],c['relationship_type_dominant'],c['average_similarity'],c['minimum_similarity'],c['strong_edge_ratio'],c['cluster_diameter'],c['canonical_image'],m['ultg'],m['nama_file'],m['kode_l1'],m['is_canonical'],m['quality_score'],c['cluster_validation_notes']])
        self.payload={'summary':self.summary,'l1':[[int(r[k]) if k in ['lebar','tinggi','ukuran_byte'] and r[k] else r[k] for k in l1_fields] for r in l1], 'l2':[[int(r[k]) if k=='jumlah_belum_dinilai' else r[k] for k in l2_fields] for r in l2], 'l3':l3_rows}

    def prepare_pairs(self,keys):
        source=FILES['pairs'];stamp=f'{source.stat().st_size}:{source.stat().st_mtime_ns}:{FILES["members"].stat().st_mtime_ns}'
        if self.db.exists():
            try:
                with closing(sqlite3.connect(self.db)) as db:
                    if db.execute('select value from metadata where key="source"').fetchone()==(stamp,):return
            except sqlite3.DatabaseError:pass
        print('Menyiapkan indeks pasangan Lapis 3...',flush=True)
        member_group={m['image_id']:g for g,ms in self.members.items() for m in ms}
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute('drop table if exists metadata')
            db.execute('drop table if exists pairs')
            db.execute('create table metadata(key text primary key,value text)')
            db.execute('create table pairs(id integer primary key,image_a text,image_b text,embedding_similarity real,phash_distance integer,dhash_distance integer,feature_match_score real,relationship_score real,relationship_type text,duplicate_confidence text,duplicate_evidence text,orb_status text,group_id text)')
            batch=[]
            for i,r in enumerate(read_csv(source),1):
                a,b=r['image_a'],r['image_b'];ga=member_group.get(a);group=ga if ga and ga==member_group.get(b) else None
                batch.append((i,a,b,number(r['embedding_similarity']),number(r['phash_distance']),number(r['dhash_distance']),number(r['feature_match_score']),number(r['relationship_score']),r['relationship_type'],r['duplicate_confidence'],r['duplicate_evidence'],r['orb_status'],group))
                if len(batch)==5000:db.executemany('insert into pairs values(?,?,?,?,?,?,?,?,?,?,?,?,?)',batch);batch=[]
            if batch:db.executemany('insert into pairs values(?,?,?,?,?,?,?,?,?,?,?,?,?)',batch)
            db.execute('create index pair_group on pairs(group_id)');db.execute('create index pair_type on pairs(relationship_type)');db.execute('create index pair_conf on pairs(duplicate_confidence)')
            db.execute('insert into metadata values("source",?)',(stamp,))

    def pairs(self,params):
        clauses=[];args=[]
        for query,column in [('group','group_id'),('type','relationship_type'),('confidence','duplicate_confidence')]:
            if params.get(query):clauses.append(column+'=?');args.append(params[query])
        if params.get('q'):
            clauses.append('(instr(lower(image_a),?)>0 or instr(lower(image_b),?)>0)');args.extend([params['q'].lower()]*2)
        where=' where '+' and '.join(clauses) if clauses else ''
        page=max(0,min(int(params.get('page','0')),100000));limit=50
        with closing(sqlite3.connect(self.db)) as db:
            db.row_factory=sqlite3.Row
            total=db.execute('select count(*) from pairs'+where,args).fetchone()[0]
            rows=[dict(r) for r in db.execute('select * from pairs'+where+' order by id limit ? offset ?',args+[limit,page*limit])]
        return {'rows':rows,'total':total,'page':page,'page_size':limit}

def runtime_node():
    base=Path(os.environ.get('USERPROFILE',str(Path.home())))/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
    exe=base/'bin/node.exe'
    if not exe.exists():exe=base/'bin/node'
    return exe,base/'node_modules'

def ensure_excel(dataset,force=False):
    marker=WORK/'excel_manifest.json'
    if not force and EXCEL.exists() and marker.exists():
        saved=json.loads(marker.read_text(encoding='utf-8'))
        if saved.get('signature')==dataset.signature:return
    node,modules=runtime_node()
    if not node.exists() or not modules.exists():
        raise RuntimeError('Runtime pembuatan Excel tidak tersedia. Jalankan pada komputer yang memiliki runtime Codex, atau pertahankan Excel dan manifest yang sudah dibuat.')
    (WORK/'workbook_data.json').write_text(json.dumps(dataset.payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    local_modules=ASSETS/'node_modules'
    if not local_modules.exists():
        if os.name=='nt':
            subprocess.run(['cmd','/c','mklink','/J',str(local_modules),str(modules)],check=True,stdout=subprocess.DEVNULL)
        else:local_modules.symlink_to(modules,target_is_directory=True)
    print('Menyiapkan Excel gabungan empat sheet...',flush=True)
    result=subprocess.run([str(node),str(ASSETS/'build_executive.mjs')],cwd=ROOT)
    # Artifact Tool can return 1 after emitting its inspection sidecar. The
    # builder creates a receipt only after export and independent ZIP readback.
    receipt=WORK/'excel_receipt.json'
    if not receipt.exists():raise RuntimeError(f'Pembuatan Excel gagal ({result.returncode})')
    info=json.loads(receipt.read_text(encoding='utf-8'))
    if info.get('source_signature')!=dataset.signature or not EXCEL.exists():raise RuntimeError('Excel belum sesuai data terbaru')
    with zipfile.ZipFile(EXCEL) as z:
        if z.testzip() is not None:raise RuntimeError('Struktur ZIP Excel tidak valid')
        doc=ET.fromstring(z.read('xl/workbook.xml'))
        sheets=[x.attrib['name'] for x in doc.findall('{*}sheets/{*}sheet')]
        if sheets!=['Eksekutif Summary','Lapis 1','Lapis 2','Lapis 3']:raise RuntimeError('Empat sheet Excel belum sesuai')
    marker.write_text(json.dumps({'signature':dataset.signature,'xlsx_sha256':file_hash(EXCEL)},indent=2),encoding='utf-8')

class AppHandler(BaseHTTPRequestHandler):
    server_version='IsolatorPortal/1.0'
    def log_message(self,fmt,*args):
        if args and str(args[1] if len(args)>1 else '') not in ('200','304'):super().log_message(fmt,*args)
    def send_json(self,obj,status=200):
        body=json.dumps(obj,ensure_ascii=False,allow_nan=False).encode('utf-8');self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers()
        if self.command!='HEAD':self.wfile.write(body)
    def serve(self,p,download=False):
        if not p.is_file():return self.send_error(404,'File tidak tersedia')
        self.send_response(200);mime=mimetypes.guess_type(str(p))[0] or 'application/octet-stream'
        self.send_header('Content-Type',mime+('; charset=utf-8' if mime.startswith('text/') else ''));self.send_header('Content-Length',str(p.stat().st_size));self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-cache')
        if download:self.send_header('Content-Disposition',f'attachment; filename="{p.name}"')
        self.end_headers()
        if self.command!='HEAD':
            with p.open('rb') as f:shutil.copyfileobj(f,self.wfile,1024*1024)
    def do_HEAD(self):self.do_GET()
    def do_GET(self):
        try:
            url=urlsplit(self.path);path=unquote(url.path);params={k:v[-1] for k,v in parse_qs(url.query).items()};data=self.server.dataset
            if path in ('/','/index.html'):return self.serve(ASSETS/'index.html')
            if path=='/api/summary':return self.send_json(data.summary)
            if path=='/api/health':return self.send_json({'status':'ok','excel_ready':EXCEL.is_file(),'app':'isolator-portal'})
            if path=='/api/lapis3/pairs':return self.send_json(data.pairs(params))
            if path=='/api/lapis3/clusters':
                rows=data.clusters
                for query,key in [('status','cluster_status'),('confidence','cluster_confidence'),('type','relationship_type_dominant'),('code','kode_l1_canonical')]:
                    if params.get(query):rows=[r for r in rows if r[key]==params[query]]
                if params.get('ultg'):rows=[r for r in rows if params['ultg'] in r['ultg'].split('; ')]
                if params.get('q'):
                    q=params['q'].lower();rows=[r for r in rows if q in (r['duplicate_group_id']+' '+r['canonical_image']+' '+' '.join(m['nama_file'] for m in data.members[r['duplicate_group_id']])).lower()]
                return self.send_json({'rows':rows,'total':len(rows),'statuses':dict(Counter(r['cluster_status'] for r in rows)),'members':sum(r['jumlah_gambar'] for r in rows)})
            if path.startswith('/api/lapis3/cluster/'):
                key=path.rsplit('/',1)[-1]
                if key not in data.cluster_by_id:return self.send_error(404)
                return self.send_json({'cluster':data.cluster_by_id[key],'members':data.members[key]})
            if path=='/dashboard/lapis3':return self.serve(ASSETS/'lapis3.html')
            if path=='/download/excel':return self.serve(EXCEL,True)
            if path.startswith('/download/lapis'):
                key=path.removeprefix('/download/lapis')
                if key in BOOKS:return self.serve(ROOT/BOOKS[key],True)
            rel=path.lstrip('/')
            if rel in DASHBOARDS.values() or rel in BOOKS.values():return self.serve(ROOT/rel)
            if rel.startswith('photos/'):rel=rel[7:]
            resolved=(ROOT/rel).resolve()
            if resolved.is_relative_to(ROOT):
                parts=resolved.relative_to(ROOT).parts
                if parts and parts[0] in PHOTO_DIRS and resolved.suffix.lower() in {'.jpg','.jpeg','.png','.webp'}:return self.serve(resolved)
            return self.send_error(404,'Halaman tidak ditemukan')
        except (BrokenPipeError,ConnectionResetError):pass
        except ValueError:return self.send_json({'error':'Parameter tidak valid'},400)
        except Exception as exc:
            print(f'Permintaan gagal: {exc}',file=sys.stderr);return self.send_json({'error':'Data tidak dapat dimuat. Periksa terminal.'},500)

def main():
    parser=argparse.ArgumentParser(description='Portal localhost evaluasi foto isolator, Lapis 1, 2, dan 3.')
    parser.add_argument('--port',type=int,default=8501,help='Port awal (default 8501); mencoba port berikutnya bila terpakai.')
    parser.add_argument('--no-browser',action='store_true',help='Jangan membuka browser otomatis.')
    parser.add_argument('--refresh-excel',action='store_true',help='Buat ulang Excel gabungan.')
    parser.add_argument('--prepare-only',action='store_true',help='Siapkan data dan Excel lalu keluar.')
    args=parser.parse_args()
    if not 1024<=args.port<=65515:parser.error('Port harus 1024 sampai 65515')
    try:
        dataset=Dataset();(WORK/'source_signature.json').write_text(json.dumps({'signature':dataset.signature}),encoding='utf-8')
        ensure_excel(dataset,args.refresh_excel)
        if args.prepare_only:print(f'Excel siap: {EXCEL}');return
        for port in range(args.port,args.port+20):
            try:server=ThreadingHTTPServer(('127.0.0.1',port),AppHandler);break
            except OSError as exc:
                if port==args.port+19:raise RuntimeError('Tidak ada port tersedia dalam rentang yang dicoba') from exc
        server.dataset=dataset
        address=f'http://127.0.0.1:{server.server_port}/'
        print(f'\nPortal siap: {address}\nExcel: {EXCEL}\nTekan Ctrl+C untuk menghentikan server.\n',flush=True)
        if not args.no_browser:threading.Timer(.3,lambda:webbrowser.open(address)).start()
        try:server.serve_forever()
        except KeyboardInterrupt:print('\nServer dihentikan.')
        finally:server.server_close()
    except Exception as exc:
        print(f'Gagal menjalankan portal: {exc}',file=sys.stderr);sys.exit(1)

if __name__=='__main__':main()
