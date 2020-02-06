import sys, re
from datetime import datetime, timedelta

DOIL=0.814
DWAT=1.059
REF =2434
NULL = 0.01

def get_gauge_tvdss_from_db_output(well_name, approximate_date): 
    with open('wt_gauges_MD_TVDSS', 'r') as gauge_db: # DBout filename hardcoded !!
        lines = [ [abs(datetime.strptime(y.split()[1],"%d.%m.%Y")-approximate_date), y.split()[0], y.split()[3], y.split()[4]] for y in [x.strip() for x in gauge_db] if y.split()[0]==well_name] 
        filter_line = [x for x in lines if x[0] == min(map(lambda x: x[0], lines))]
        #print(filter_line) # debug
        return float(filter_line[0][3]) # 

def derivative(x1, x2, t1, t2):
    dx = x2 - x1
    dt = (t2 - t1).seconds/60/60
    if dt==0 or x2==NULL or x1==NULL or t1.year==1900:
        return 0
    else:
        return dx/dt



def read_WT_hist_file(file_name):
    well = ''
    dates, qoil, qwat, bhp, thp, wcut = [], [], [], [], [], []

    with open(file_name,'r') as input_file:
        all_content = ''.join([x for x in input_file])
        #all_before_htab = re.search(r"[\w\W]*HTAB", all_content) 
        #all_after_htab = re.search("ENDH[\w\W]*", all_content)
        
        htab_lines = re.findall(r"(.*)\n",  re.search(r"HTAB.*\n([\W\w]*)ENDH", all_content).group(1))
        htab_records = [x for x in htab_lines if x[0:2]!="--"]
        
        for x in htab_records:
            words = re.split(r'\s+|/', x)
            well = words[0]
            dates.append(datetime.strptime(words[1], "%d.%m.%Y")+timedelta(hours=float(words[8])))
            qoil.append(float(words[2]))
            qwat.append(float(words[3]))
            bhp.append(float(words[4]))
            thp.append(words[5])

    g_tvdss = get_gauge_tvdss_from_db_output(well, dates[0]) 
    wcut = [w/(o+w) for o,w in zip(qoil, qwat)]
    mix_den = [(1-w)*DOIL+w*DWAT for w in wcut]
    bhp_mix = [p+(REF-g_tvdss)*9.81*(dm-DOIL)/100 if p > 0.01 else p for p,dm in zip(bhp, mix_den)]

    for d,dt,x,y,w in zip(mix_den, dates, bhp, bhp_mix, wcut):
        #print(f"{well} {dt:%d.%m.%Y} {g_tvdss:.2f} {d:.3f} {w:.2f} {x:.2f} {y:.2f}")
        print(f"{well} {dt:%d.%m.%Y} {g_tvdss:.2f} {d:.3f} {w:.2f} {x:.2f} {y:.2f}") # htab format

    #print(well)
    #print(dates)
    #print(qoil)
    #print(qwat)
    #print(bhp)
    #print(thp)



read_WT_hist_file(sys.argv[1])

# TODO get TVDSS for current WT (BasPro) 
#     partly DONE(needs check)
#     unloads odd values with wrong MD-TVDSS for PLT-tests (need test filter in oracle-query)
        
