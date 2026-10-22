"""Render actual architecture illustrations to SVG/PNG; these are not run evidence."""
from pathlib import Path
from html import escape
from PIL import Image,ImageDraw,ImageFont
from hospital.live import ROOT


def render(path,title,boxes,edges,width=1280,height=680):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    img=Image.new('RGB',(width,height),'#f8fafc')
    draw=ImageDraw.Draw(img)
    try:
        font=ImageFont.truetype('arial.ttf',19)
    except OSError:
        font=ImageFont.load_default(size=19)
    draw.text((30,22),title,fill='#0f172a',font=font)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><defs><marker id="a" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#475569"/></marker></defs><rect width="100%" height="100%" fill="#f8fafc"/><text x="30" y="40" font-size="24" font-family="sans-serif">{escape(title)}</text>']
    for (x1,y1,x2,y2) in edges:
        draw.line((x1,y1,x2,y2),fill='#475569',width=3)
        import math
        angle=math.atan2(y2-y1,x2-x1)
        draw.polygon([(x2,y2),(x2-12*math.cos(angle-.45),y2-12*math.sin(angle-.45)),
                      (x2-12*math.cos(angle+.45),y2-12*math.sin(angle+.45))],fill='#475569')
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#475569" stroke-width="3" marker-end="url(#a)"/>')
    for x,y,w,h,label in boxes:
        draw.rounded_rectangle((x,y,x+w,y+h),radius=12,fill='#dbeafe',outline='#2563eb',width=2)
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#dbeafe" stroke="#2563eb"/>')
        for i,line in enumerate(label.split('|')):
            draw.text((x+12,y+12+i*25),line,font=font,fill='#0f172a')
            svg.append(f'<text x="{x+12}" y="{y+30+i*25}" font-size="19" font-family="sans-serif">{escape(line)}</text>')
    svg.append('</svg>')
    path.with_suffix('.svg').write_text(''.join(svg),encoding='utf-8')
    img.save(path.with_suffix('.png'))


def main():
    boxes=[(30,100,225,105,'Shared hospital source|CSV / JSON + events'),(340,100,225,105,'Snowpipe + Bronze|Native rows / batch'),
           (650,100,245,105,'Silver|Stream / Task / MERGE'),(980,100,260,105,'dbt staging|Typed sources'),
           (980,300,260,105,'dbt intermediate|History / joins / snapshot'),(650,300,245,105,'Gold|Admission fact + patients'),
           (340,300,225,105,'Security|Tags / native masks'),(30,300,225,105,'Analyst|Masked Gold SELECT'),
           (30,525,350,100,'Monitoring + alerts|Freshness / counts / runs|Query history'),
           (470,525,360,100,'PR tests -> DEV integration|Main + environment approval'),
           (930,525,310,100,'PROD service deployment|Migrations + dbt + verification')]
    edges=[(255,150,340,150),(565,150,650,150),(895,150,980,150),(1110,205,1110,300),
           (980,350,895,350),(650,350,565,350),(340,350,255,350),(455,205,285,240),(285,240,285,500),(285,500,205,525),
           (770,405,205,525),(830,575,930,575),(1080,525,800,405)]
    render(ROOT/'docs/PHASE10/architecture_diagram','Hospital admissions: same data path inside isolated DEV / PROD',boxes,edges)
    boxes=[(490,80,300,80,'SYSADMIN|Authorized setup'),(490,230,300,80,'DE_ADMIN|Inherits three children'),
           (50,420,330,110,'DE_ENGINEER|DEV read/write ownership|No PROD model writes'),
           (470,420,330,110,'DE_ANALYST|PROD approved Gold SELECT|Masked PII; no raw access'),
           (880,420,330,110,'DE_DEPLOYER|PROD automation ownership|Separate protected key')]
    edges=[(640,160,640,230),(520,310,215,420),(640,310,635,420),(760,310,1045,420)]
    render(ROOT/'docs/PHASE10/role_hierarchy_diagram','Inheritance arrows: parent inherits child; never the reverse',boxes,edges)
    boxes=[(40,120,260,100,'Python event producer|Native Streaming SDK'),(410,120,270,100,'Snowpipe / Bronze|Raw + server load time'),
           (850,120,320,100,'Stream / Task / Silver MERGE|Quarantine + unique admissions'),(410,380,320,100,'Checkpoint + recovery|Retained source / channel ID|Server committed offset'),
           (850,380,320,100,'Metrics|Event / send -> loaded_at|p50 / p95 / events per minute')]
    edges=[(300,170,410,170),(680,170,850,170),(545,220,545,380),(1020,220,1020,380)]
    render(ROOT/'docs/PHASE7/stream_architecture_diagram','Native row streaming; batch bootstrap shares the same Bronze / Silver',boxes,edges)
    print('Rendered architecture, role hierarchy and ingestion diagrams as SVG and PNG')


if __name__=='__main__':
    main()
