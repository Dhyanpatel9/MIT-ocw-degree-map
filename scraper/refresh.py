#!/usr/bin/env python3
"""Refresh the MIT undergrad -> OpenCourseWare map.

Pulls every undergraduate degree chart from catalog.mit.edu, pulls the full
course list from ocw.mit.edu/sitemap.xml, matches them, and writes
data/courses.json and data/courses.csv.

Usage:  pip install -r scraper/requirements.txt
        python3 scraper/refresh.py
"""
import csv, json, re, sys, time, urllib.request
from datetime import date
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
CATALOG = "https://catalog.mit.edu"
UA = {"User-Agent": "mit-ocw-map/1.0 (open-source course map)"}

def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if attempt == 2: raise
            time.sleep(2)

# Courses renumbered (mostly MIT's 2022 EECS renumbering): new -> old numbers on OCW
OLD = {'6.100A':['6.0001','6.100L'],'6.100B':['6.0002'],'6.1000':['6.0001','6.100L'],'6.100L':['6.0001'],
 '6.1010':['6.009'],'6.1020':['6.031','6.005'],'6.1040':['6.170'],'6.1060':['6.172'],'6.1100':['6.035'],
 '6.1200':['6.042'],'6.1210':['6.006'],'6.1220':['6.046'],'6.1400':['6.045'],'6.1800':['6.033'],
 '6.1810':['6.S081','6.828'],'6.1910':['6.004'],'6.1920':['6.175'],'6.2000':['6.002'],'6.2040':['6.101'],
 '6.2050':['6.111'],'6.2060':['6.115'],'6.2200':['6.061'],'6.2220':['6.131'],'6.2300':['6.013'],
 '6.2500':['6.012'],'6.3000':['6.003'],'6.3010':['6.011'],'6.3100':['6.302'],'6.3400':['6.02'],
 '6.3700':['6.041'],'6.3800':['6.008'],'6.3900':['6.036'],'6.4100':['6.034'],'6.4200':['6.141'],
 '6.4400':['6.837'],'6.4590':['6.805'],'6.4800':['6.021'],'6.4810':['6.022'],'6.5080':['6.816'],
 '6.5110':['6.820'],'6.5660':['6.858'],'6.5831':['6.830'],'6.5840':['6.824'],'6.5900':['6.823'],
 '6.7900':['6.867'],'6.8301':['6.819'],'6.8611':['6.806','6.864'],'6.8701':['6.047'],'6.8711':['6.802'],
 '5.601':['5.60'],'5.602':['5.60'],'5.611':['5.61'],'5.612':['5.61'],'15.0111':['15.010','15.011'],
 '15.0112':['15.010','15.011'],'15.072':['15.071'],'6.4110':['6.825'],'6.3020':['6.341'],
 '6.7201':['6.255','15.093'],'6.7200':['6.251'],'6.3720':['6.401']}
# Title matches reviewed by hand and rejected (different course, similar title)
NO_MATCH = {'18.C06', '11.188', '6.1903', '6.1904'}
# OCW pages that cover more than one course number
EXTRA = {'8.14': '8.13'}

GIR = [('18.01','Calculus I','R'),('18.02','Calculus II','R'),('8.01','Physics I','R'),('8.02','Physics II','R'),
       ('5.111','Principles of Chemical Science','A'),('5.112','Principles of Chemical Science','A'),
       ('3.091','Introduction to Solid-State Chemistry','A'),('7.012','Introductory Biology','A'),
       ('7.013','Introductory Biology','A'),('7.014','Introductory Biology','A'),('7.015','Introductory Biology','A'),
       ('7.016','Introductory Biology','A')]

CODE_ROW = re.compile(r'^(or )?([0-9]{1,2}[A-Z]?|[A-Z]{2,4})\.[0-9A-Z]{1,6}')
CODES = re.compile(r'([0-9]{1,2}[A-Z]?|[A-Z]{2,4})\.[0-9A-Z]{1,6}(?:\[J\]|J)?')

def norm(s):
    s = s.upper().replace(' ', '').replace('[J]', '')
    s = re.sub(r'SC$', '', s); s = re.sub(r'J$', '', s)
    return s

def tnorm(s):
    s = s.lower().replace('&', 'and')
    s = re.sub(r'\(ci-[a-z]+\)', '', s)
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', s)).strip()

def school_of(code):
    groups = {'Architecture & Planning':'4 4-B 11', 'Engineering':'1-ENG 2 2-A 2-OE 3 3-A 3-C 6-3 6-4 6-5 10 10-B 10-C 10-ENG 16 16-ENG 20 22 22-ENG',
              'Science':'5 7 8 9 12 18 18-C', 'Management (Sloan)':'15-1 15-2 15-3',
              'Interdisciplinary':'5-7 1-12 6-7 6-9 6-14 11-6 21 21E 21S'}
    for name, codes in groups.items():
        if code in codes.split(): return name
    return 'Humanities, Arts & Social Sciences'

# ---------------- OpenCourseWare ----------------
def load_ocw():
    sm = get('https://ocw.mit.edu/sitemap.xml')
    slugs = re.findall(r'/courses/([^/<]+)/sitemap\.xml', sm)
    by_num, by_title = {}, {}
    for s in slugs:
        p = s.split('-')
        if p[0] == 'res': continue
        year = int(p[-1]) if p[-1].isdigit() and len(p[-1]) == 4 else 0
        by_num.setdefault(norm(p[0] + '.' + p[1]), []).append((year, s))
        rest = p[2:]
        if rest and rest[-1].isdigit() and len(rest[-1]) == 4:
            rest = rest[:-1]
            while rest and rest[-1] in ('spring','fall','summer','winter','january','iap','semester'): rest.pop()
        by_title.setdefault(p[0] + '|' + ' '.join(rest), []).append(s)
    for v in by_num.values(): v.sort(reverse=True)
    return slugs, by_num, by_title

def match(code, title, by_num, by_title):
    k = norm(code)
    if k in EXTRA: k2 = norm(EXTRA[k]); return ('Y', by_num[k2][0][1], 'listed with ' + EXTRA[k]) if k2 in by_num else ('N','','')
    if k in by_num: return 'Y', by_num[k][0][1], ''
    if k in NO_MATCH: return 'N', '', ''
    for o in OLD.get(k, []):
        if norm(o) in by_num: return 'O', by_num[norm(o)][0][1], o
    tt = tnorm(title)
    hit = by_title.get(k.split('.')[0].lower() + '|' + tt)
    if hit and len(tt.split()) >= 2: return 'O', hit[-1], 'same title'
    return 'N', '', ''

# ---------------- Catalog ----------------
def program_links():
    soup = BeautifulSoup(get(CATALOG + '/degree-charts/'), 'html.parser')
    out, seen = [], set()
    for a in soup.select('a[href*="/degree-charts/"]'):
        t = a.get_text(' ', strip=True).replace('​', '')
        if not re.search(r'\((Course|CMS|STS|6-4)', t): continue
        href = a['href'].replace('catalog-dev.mit.edu', 'catalog.mit.edu')
        if href.startswith('/'): href = CATALOG + href
        if href in seen: continue
        seen.add(href); out.append((t, href))
    return out

def parse_program(html):
    """Yield (section, code, title, requirement) for each course on a degree chart.
    requirement: R = required, A = required, choose one from group, E = elective option."""
    soup = BeautifulSoup(html, 'html.parser')
    trs = soup.select('table.sc_courselist tr') or soup.select('table tr')
    hdr = sec = ''; sel = False; sel_mode = None; sel_one = False; pick_each = False
    for i, tr in enumerate(trs):
        cls = ' '.join(tr.get('class', []))
        td = tr.find('td')
        if not td: continue
        c = re.sub(r'\s+', ' ', td.get_text(' ')).strip()
        if 'areaheader' in cls:
            hdr = sec = re.sub(r'\s+\d+$', '', c); sel = False; sel_mode = None
            if re.search(r'elective|units|option|thesis', c, re.I): pick_each = False
            continue
        if re.match(r'^(Select|Choose)', c, re.I):
            if re.search(r'each of', c, re.I): pick_each = True; continue
            sec = re.sub(r'\s+\d+$', '', c); sel = True; sel_mode = None
            sel_one = bool(re.search(r'\bone\b|\b12 units\b', c, re.I)) and not re.search('elective', hdr, re.I)
            continue
        if not CODE_ROW.match(c): continue
        indented = td.find('div', style=re.compile('margin-left')) is not None
        is_or = 'orclass' in cls
        if sel and sel_mode is None and not is_or: sel_mode = 'ind' if indented else 'flat'
        if sel and sel_mode == 'ind' and not indented and not is_or: sel = False; sel_mode = None; sec = hdr
        nxt = trs[i + 1] if i + 1 < len(trs) else None
        next_or = nxt is not None and 'orclass' in ' '.join(nxt.get('class', []))
        if sel: req = 'A' if sel_one else 'E'
        elif indented: req = 'A' if pick_each else 'E'
        elif is_or or next_or: req = 'A'
        elif re.search('elective', hdr, re.I): req = 'E'
        else: req = 'R'
        tds = tr.find_all('td')
        title = re.sub(r'\s+\d$', '', re.sub(r'\s+', ' ', tds[1].get_text(' ')).strip()) if len(tds) > 1 else ''
        codes = [m.group(0) for m in CODES.finditer(c)]
        for code in codes:
            yield sec, code.replace('[J]', 'J'), (title if len(codes) == 1 else ''), req, is_or

EXTRAS = json.loads((Path(__file__).parent / 'extras.json').read_text())

def main():
    print('Loading OCW course list…'); slugs, by_num, by_title = load_ocw()
    print(f'  {len(slugs)} OCW courses')
    links = program_links(); print(f'{len(links)} undergraduate programs')
    progs, rows = [], []
    def add_program(code, name, url, items):
        seen, cnt, rq = set(), {'Y':0,'O':0,'N':0}, {'r':0,'ro':0}
        for sec, num, title, req, alt in items:
            st, slug, via = match(num, title, by_num, by_title)
            j = EXTRAS['joint'].get(num)
            if st == 'N' and j:
                st2, slug2, _ = match(j, '', by_num, by_title)
                if slug2: st, slug, via = 'O', slug2, 'same class as ' + j
            if num in EXTRAS['override']: st, slug, via = EXTRAS['override'][num]
            if re.search(r'\.(TH|UR|UAR)', num, re.I): st = req = '-'
            rows.append(dict(p=code, q=req, sec=sec, num=num, t=title, s=st, slug=slug, via=via, alt=alt,
                             more=EXTRAS['links'].get(num, [])))
            if num not in seen and st != '-':
                seen.add(num); cnt[st] += 1
                if req == 'R': rq['r'] += 1; rq['ro'] += st in 'YO'
        progs.append(dict(code=code, name=name, school='All' if code == 'GIR' else school_of(code), url=url,
                          rq=rq['r'], rqo=rq['ro'], **cnt))
    add_program('GIR', 'Core requirements (all majors)', CATALOG + '/mit/undergraduate-education/general-institute-requirements/',
                [('Science requirement: one subject from each line', c, t, r, False) for c, t, r in GIR])
    for text, url in links:
        m = re.search(r'\(([^)]*)\)\s*$', text)
        code = re.sub(r'Course\s|Second Major', '', m.group(1)).replace('\xa0', ' ').strip() if m else text
        if code.startswith('STS'): code = 'STS'
        name = re.sub(r'\s*\([^)]*\)\s*$', '', text)
        print('  ', code, name)
        add_program(code, name, url, list(parse_program(get(url))))
        time.sleep(0.5)
    order = 'GIR 4 4-B 11 1-ENG 2 2-A 2-OE 3 3-A 3-C 6-3 6-4 6-5 10 10-B 10-C 10-ENG 16 16-ENG 20 22 22-ENG 5 7 8 9 12 18 18-C 14-1 14-2 17 21A CMS 21G 21H 21L 21M 21T 21W 24-1 24-2 STS 21 21E 21S 15-1 15-2 15-3 5-7 1-12 6-7 6-9 6-14 11-6'.split()
    progs.sort(key=lambda p: order.index(p['code']) if p['code'] in order else 99)
    if len(progs) < 40 or len(rows) < 1000:
        sys.exit(f'Sanity check failed ({len(progs)} programs, {len(rows)} rows) - not overwriting data')
    out = ROOT / 'data'; out.mkdir(exist_ok=True)
    meta = dict(updated=date.today().isoformat(), ocw_courses=len(slugs))
    (out / 'courses.json').write_text(json.dumps(dict(meta=meta, progs=progs, rows=rows)))
    L = {'Y':'On OCW','O':'On OCW (other number)','N':'Not on OCW','-':'Thesis / research'}
    Q = {'R':'Required','A':'Required - choose one','E':'Elective option','-':'Thesis / research'}
    with open(out / 'courses.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['Program','Program name','Required?','Catalog section','Course','Title','OCW status','OCW number used','Course materials link','More free materials'])
        names = {p['code']: p['name'] for p in progs}
        for r in rows:
            w.writerow([r['p'], names[r['p']], Q[r['q']], r['sec'], r['num'], r['t'], L[r['s']], r['via'],
                        f"https://ocw.mit.edu/courses/{r['slug']}/" if r['slug'] else '', ' '.join(u for _, u in r['more'])])
    u = {r['num']: r['s'] for r in rows if r['s'] != '-'}
    print(f"Done: {len(progs)} programs, {len(u)} courses; on OCW {sum(v=='Y' for v in u.values())}, "
          f"other number {sum(v=='O' for v in u.values())}, not on OCW {sum(v=='N' for v in u.values())}")

if __name__ == '__main__':
    main()
