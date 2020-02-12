import sys, re, os
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
    dates, qoil, qwat, bhp, thp, wcut, hours = [], [], [], [], [], [], []

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
            hours.append(words[8])

    g_tvdss = get_gauge_tvdss_from_db_output(well, dates[0]) 
    wcut = [w/(o+w) for o,w in zip(qoil, qwat)]
    mix_den = [(1-w)*DOIL+w*DWAT for w in wcut]
    bhp_mix = [p+(REF-g_tvdss)*9.81*(dm-DOIL)/100 if p > 0.01 else p for p,dm in zip(bhp, mix_den)]


    regime = [1 if x+y > NULL else 0 for x,y in zip(qoil, qwat) ]
    regime_shift = regime[:] 
    regime_shift.insert(-1,regime_shift[-1])
    regime_shift.pop(0)
    ch_moments = [0 if x==y else 1 for x,y in zip(regime, regime_shift)]
    ch_indexes = [i for i,x in enumerate(ch_moments) if x==1]  

    #print(regime)
    #print(regime_shift)
    #print(ch_moments)
    #print(ch_indexes)


    cc = 0
    ccc = []
    for i in enumerate(ch_moments):
        if i[0] in ch_indexes:
            cc = i[0]
        ccc.append(cc)
    #print(ccc)

    date_indexes = [x[0] if x[1]==0 else x[1] for x in enumerate(ccc)]
    #print(date_indexes)
    deltas = [x-dates[i] for x,i in zip(dates,date_indexes)]

    #for i in range(len(dates)):
    #    print(dates[i], dates[date_indexes[i]], deltas[i].total_seconds()/60/60)

    dt_deltas = [x.total_seconds()/60/60 if x.total_seconds()/60/60 < 1 else 0 for x in deltas]
    #print(dt_deltas)



    for mix_den_i, dates_i, bhp_i,bhp_mix_i, wcut_i, qoil_i, qwat_i, thp_i, hours_i, dt_deltas_i in zip(mix_den, dates, bhp, bhp_mix, wcut, qoil, qwat, thp, hours, dt_deltas):
        print(f"{well} {dates_i:%d.%m.%Y %H:%M:%S} {g_tvdss:.2f} {wcut_i:.3f} {bhp_i:.2f} {bhp_mix_i:.2f} {mix_den_i:.3f} {dt_deltas_i:.5f}") # debug format
        #print(f"{well} {dates_i:%d.%m.%Y} {qoil_i:10.3f} {qwat_i:10.3f} {bhp_mix_i:10.2f} {thp_i} 1 Hours {hours_i}") # htab format

    #print(well)
    #print(dates)
    #print(qoil)
    #print(qwat)
    #print(bhp)
    #print(thp)



def get_all_files1():
    destination_folder = "wt_out"

    for root, dirs, files in os.walk(sys.argv[1]):
        for item in files:
            #print(os.path.join(root,item))
            pass


#get_all_files()
get_all_files1()

#read_WT_hist_file(sys.argv[1])

# TODO smooth density change when well goes to PBU/from PBU
# TODO find out how density influences the results of PI calculation!!
# TODO get TVDSS for current WT (BasPro) > partly DONE(needs check) > gives odd values with wrong MD-TVDSS for PLT-tests (need test filter in oracle-query)
        
