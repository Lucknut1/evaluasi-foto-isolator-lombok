import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url))),work=path.join(root,'outputs/portal_work'),out=path.join(root,'outputs/portal');
const payload=JSON.parse(await fs.readFile(path.join(work,'workbook_data.json'),'utf8')),s=payload.summary;
const signature=JSON.parse(await fs.readFile(path.join(work,'source_signature.json'),'utf8')).signature;
const wb=Workbook.create(),summary=wb.worksheets.add('Eksekutif Summary'),l1=wb.worksheets.add('Lapis 1'),l2=wb.worksheets.add('Lapis 2'),l3=wb.worksheets.add('Lapis 3');
const navy='#173B58',ink='#203042',gray='#607487',pale='#EAF2F7',font='Arial';
const header={fill:navy,font:{name:font,size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true};
for(const sheet of [summary,l1,l2,l3]){sheet.showGridLines=false;sheet.getRange('A2').format.font={name:font,size:15,bold:true,color:navy};}
summary.tabColor=navy;l1.tabColor='#176B9A';l2.tabColor='#5987AD';l3.tabColor='#7FA6C4';
summary.getRange('A2').values=[['Ringkasan Eksekutif Evaluasi Foto Isolator']];
summary.getRange('A3').values=[['Unit Lapis 1/2 = foto; unit Lapis 3 = pasangan dan cluster. Denominator tiap lapis berbeda.']];
summary.getRange('A3:H3').format.font={name:font,size:10,italic:true,color:gray};
summary.getRange('A5:D5').values=[['Lapis','Indikator','Jumlah','Satuan']];summary.getRange('A5:D5').format=header;
const metrics=[
 ['Lapis 1','Foto dievaluasi',s.l1.total,'foto'],['Lapis 1','Sesuai (S)',s.l1.codes.S||0,'foto'],['Lapis 1','Non-sesuai',s.l1.total-(s.l1.codes.S||0),'foto'],['Lapis 1','Perlu review',s.l1.review,'foto'],
 ['Lapis 2','Foto dianalisis',s.l2.total,'foto'],['Lapis 2','Sampel audit',s.l2.sample,'foto'],['Lapis 2','Foto dengan ciri belum dinilai',s.l2.with_gaps,'foto'],['Lapis 2','Sel ciri belum dinilai',s.l2.gap_cells,'sel'],
 ['Lapis 3','Foto dianalisis',s.l3.images,'foto'],['Lapis 3','Pasangan diperiksa',s.l3.pairs,'pasangan'],['Lapis 3','Cluster terbentuk',s.l3.clusters,'cluster'],['Lapis 3','Foto dalam cluster',s.l3.members,'foto'],
 ['Lapis 3','VALID (otomatis)',s.l3.statuses.VALID||0,'cluster'],['Lapis 3','NEED_REVIEW',s.l3.statuses.NEED_REVIEW||0,'cluster'],['Lapis 3','SPLIT_RECOMMENDED',s.l3.statuses.SPLIT_RECOMMENDED||0,'cluster']
];
summary.getRange('A6:D20').values=metrics;summary.getRange('A6:D20').format.font={name:font,size:10,color:ink};summary.getRange('C6:C20').format.numberFormat='#,##0';
summary.getRange('F5:H5').values=[['Kode Lapis 1','Jumlah foto','Porsi L1']];summary.getRange('F5:H5').format=header;
const codes=['S','J','O','B','P','K','H','D','L'];codes.forEach((k,i)=>{const row=6+i;summary.getRange('F'+row+':G'+row).values=[[k,s.l1.codes[k]||0]];summary.getRange('H'+row).formulas=[['=G'+row+'/$C$6']];});
summary.getRange('G6:G14').format.numberFormat='#,##0';summary.getRange('H6:H14').format.numberFormat='0.0%';
summary.getRange('F17:H17').values=[['Status cluster','Jumlah','Porsi cluster']];summary.getRange('F17:H17').format=header;
['VALID','NEED_REVIEW','SPLIT_RECOMMENDED'].forEach((k,i)=>{const row=18+i;summary.getRange('F'+row+':G'+row).values=[[k,s.l3.statuses[k]||0]];summary.getRange('H'+row).formulas=[['=G'+row+'/$C$16']];});summary.getRange('H18:H20').format.numberFormat='0.0%';
summary.getRange('A23:D23').values=[['Lapis','Prioritas tindak lanjut','Status','Keterangan']];summary.getRange('A23:D23').format=header;
summary.getRange('A24:D26').values=[['Lapis 1','Tinjau foto confidence rendah','Triase otomatis','Kode keputusan tersimpan'],['Lapis 2','Audit 1.500 foto dan lengkapi ciri','Estimasi otomatis','Sebelas ciri; kode L1 sebagai konteks'],['Lapis 3','Review cluster dan usulan pemisahan','Validasi algoritme','VALID tidak berarti audit manusia selesai']];summary.getRange('A24:D26').format={font:{name:font,size:10,color:ink},wrapText:true,verticalAlignment:'center'};summary.getRange('24:26').format.rowHeight=40;
summary.getRange('A29:E29').values=[['Ciri Lapis 2','Belum dinilai','Tidak jelas','NA','Total foto']];summary.getRange('A29:E29').format=header;
summary.getRange('A30:E40').values=s.l2.features.map(f=>[f.label,f.counts.belum_dinilai||0,f.counts.tidak_jelas||0,f.counts.NA||0,s.l2.total]);summary.getRange('B30:E40').format.numberFormat='#,##0';
summary.getRange('A42').values=[['Lapis 3: satu baris per anggota cluster. Jumlah cluster dihitung unik, bukan menjumlahkan ukuran cluster berulang.']];
summary.getRange('A44').values=[['Bukti seluruh pasangan tersedia pada Excel Lapis 3 lengkap melalui menu Lapis 3 di portal.']];summary.getRange('A42:H44').format.font={name:font,size:10,italic:true,color:gray};
for(const [col,width] of [['A:A',23],['B:B',37],['C:C',23],['D:D',36],['E:E',12],['F:F',27],['G:G',17],['H:H',19]])summary.getRange(col).format.columnWidth=width;
const featureNames=['ragu2','cakupan_foto','jumlah_renteng_terbaca','arah_isolator','bahan_isolator','cahaya','ketajaman','noise','halangan','isi_frame_terbanyak','bagian_renteng_terlihat'];
const defs=[
 [l1,'Keputusan Foto, Lapis 1','Satu baris per foto. Hasil keputusan disalin dari keluaran Lapis 1 yang tersimpan.',['ULTG','Nama foto','Kode L1','Keputusan','Confidence','Perlu review','Alasan','Lebar (px)','Tinggi (px)','Ukuran (byte)','Status baca'],payload.l1,[24,48,11,30,15,16,90,14,14,18,15]],
 [l2,'Ciri Foto, Lapis 2','Satu baris per foto analisis. Nilai ciri merupakan estimasi otomatis; belum_dinilai, NA, dan tidak_jelas berbeda dari nol.',['ULTG','Nama foto','Kode L1','Sampel audit',...featureNames,'Jumlah belum dinilai','Validasi manual','Catatan reviewer'],payload.l2,[24,48,11,15,...featureNames.map(()=>25),21,20,50]],
 [l3,'Cluster dan Anggota, Lapis 3','Satu baris per anggota cluster. Ukuran dan skor cluster berulang pada anggotanya; jangan dijumlahkan.',['Cluster','Status cluster','Ukuran cluster','Confidence cluster','Relasi dominan','Rata-rata similarity','Minimum similarity','Rasio edge kuat','Diameter cluster','Foto canonical','ULTG','Nama foto anggota','Kode L1 anggota','Canonical','Skor mutu','Catatan validasi'],payload.l3,[17,26,17,22,24,23,23,22,19,60,24,48,18,16,18,55]]
];
for(const [sheet,title,note,headers,rows,widths] of defs){sheet.getRange('A2').values=[[title]];sheet.getRange('A3').values=[[note]];sheet.getRange('A3:R3').format.font={name:font,size:10,italic:true,color:gray};sheet.getRangeByIndexes(3,0,1,headers.length).values=[headers];sheet.getRangeByIndexes(3,0,1,headers.length).format=header;sheet.getRange('4:4').format.rowHeight=34;for(let i=0;i<rows.length;i+=1000)sheet.getRangeByIndexes(4+i,0,Math.min(1000,rows.length-i),headers.length).values=rows.slice(i,i+1000);const last=String.fromCharCode(64+headers.length);sheet.tables.add('A4:'+last+(rows.length+4),true,'Table'+sheet.name.replaceAll(' ','')).style='TableStyleMedium2';sheet.freezePanes.freezeRows(4);sheet.freezePanes.freezeColumns(2);widths.forEach((w,i)=>sheet.getRangeByIndexes(0,i,1,1).format.columnWidth=w);}
l3.getRange('F5:I'+(payload.l3.length+4)).format.numberFormat='0.000';l3.getRange('O5:O'+(payload.l3.length+4)).format.numberFormat='0.000';
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Eksekutif Summary!A5:D20',tableMaxRows:16,tableMaxCols:4,maxChars:2500,include:'values'})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
for(const [sheet,range] of [['Eksekutif Summary','A1:H21'],['Lapis 1','A1:G10'],['Lapis 2','A1:I10'],['Lapis 3','A1:I10']]){const png=await wb.render({sheetName:sheet,range,scale:1,format:'png'});await fs.writeFile(path.join(work,'preview_'+sheet.replaceAll(' ','_')+'.png'),new Uint8Array(await png.arrayBuffer()));}
const target=path.join(out,'Ringkasan_Eksekutif_Lapis_1_2_3.xlsx');await fs.mkdir(out,{recursive:true});const book=await SpreadsheetFile.exportXlsx(wb);await book.save(target);
await fs.writeFile(path.join(work,'excel_receipt.json'),JSON.stringify({source_signature:signature,rows:[payload.l1.length,payload.l2.length,payload.l3.length]}));
console.log('Excel gabungan tersimpan.');
