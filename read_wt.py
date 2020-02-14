import sys, re, os
from datetime import datetime, timedelta

DOIL=0.814
DWAT=1.059
REF =2434
NULL = 0.01
WCUT_TRIGGER = 0.05 # check if i have written somewhere 0.025 (PO or anywhere else)
DC = 0.75 # hours for mixture separation or vice versa

def get_gauge_tvdss_from_db_output(well_name, approximate_date): 
    with open('wt_gauges_MD_TVDSS', 'r') as gauge_db: # DBout filename hardcoded !!
        lines = [ [abs(datetime.strptime(y.split()[1],"%d.%m.%Y")-approximate_date), y.split()[0], y.split()[3], y.split()[4]] for y in [x.strip() for x in gauge_db] if y.split()[0]==well_name] 
        filter_line = [x for x in lines if x[0] == min(map(lambda x: x[0], lines))]
        #print(filter_line) # debug
        return (float(filter_line[0][2]) ,float(filter_line[0][3])) # (gauge_md, gauge_tvdss)

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
    all_content, all_before_htab, all_after_htab = '','',''
    recalculated_htab='\n--well	date	Qoil	Qwat	BHP	THP	WEFA	HOURs\n' # TODO find out how to save comment lines from HTAB section

    # read input file
    with open(file_name,'r') as input_file:
        all_content = ''.join([x for x in input_file])
        all_before_htab = re.search(r"[\w\W]*HTAB", all_content).group(0)
        all_after_htab = re.search("ENDH[\w\W]*", all_content).group(0)
        
        htab_lines = re.findall(r"(.*)\n",  re.search(r"HTAB.*\n([\W\w]*)ENDH", all_content).group(1))
        htab_records = [x for x in htab_lines if x[0:2]!="--" and len(x)>0]
        for x in htab_records:
            words = re.split(r'\s+|/|--', x) 
            well = words[0]
            dates.append(datetime.strptime(words[1], "%d.%m.%Y")+timedelta(hours=float(words[8])))
            qoil.append(float(words[2]))
            qwat.append(float(words[3]))
            bhp.append(float(words[4]))
            thp.append(words[5])
            hours.append(words[8])
    wcut = [w/(o+w) for o,w in zip(qoil, qwat)]


    # recalculate or not 
    if max(qoil)==0:
        return (all_content, "Injector, no recalculation")
    elif max(wcut) < WCUT_TRIGGER:
        return (all_content, f"Wcut is less {WCUT_TRIGGER}, no recalculation ")
    else:
        regime = [1 if x+y > NULL else 0 for x,y in zip(qoil, qwat) ]
        ch_moments = [0 if x==y else 1 for x,y in zip(regime, regime[1:]+[regime[-1]])]
        ch_indexes = [i for i,x in enumerate(ch_moments) if x==1]  
        
        cc, ccc = 0, []
        for i in enumerate(ch_moments):
            if i[0] in ch_indexes:
                cc = i[0]
            ccc.append(cc)
        #print(ccc) # additional array of change regime indexes
        date_indexes = [x[0] if x[1]==0 else x[1] for x in enumerate(ccc)]
        deltas = [x-dates[i] for x,i in zip(dates,date_indexes)]
        #for i in range(len(dates)):
        #    print(dates[i], dates[date_indexes[i]], deltas[i].total_seconds()/60/60)
        dt_deltas = [x.total_seconds()/60/60 if x.total_seconds()/60/60 < DC else 0 for x in deltas] # print hours from regime change within one hour
        #print(dt_deltas)

        gauge_md, gauge_tvdss  = get_gauge_tvdss_from_db_output(well, dates[0]) 
        mix_den = [(1-w)*DOIL+w*DWAT for w in wcut]
        mix_den_smooth = [x if dt==0 else x*dt/DC+mix_den[c]*(DC-dt)/DC for x,c,dt in zip(mix_den,ccc,dt_deltas)]
        bhp_mix = [p+(REF-gauge_tvdss)*9.81*(dm-DOIL)/100 if p > 0.01 else p for p,dm in zip(bhp, mix_den_smooth)]

        for mix_den_i, mix_den_smooth_i, dates_i, bhp_i,bhp_mix_i, wcut_i, qoil_i, qwat_i, thp_i, hours_i, dt_deltas_i in zip(mix_den, mix_den_smooth, dates, bhp, bhp_mix, wcut, qoil, qwat, thp, hours, dt_deltas):
            #recalculated_htab += f"{well} {dates_i:%d.%m.%Y %H:%M:%S} {gauge_tvdss:.2f} {wcut_i:.3f} {bhp_i:.2f} {bhp_mix_i:.2f} {mix_den_i:.3f} {mix_den_smooth_i:.3f} {dt_deltas_i:.5f}\n" # debug format
            recalculated_htab += f"{well} {dates_i:%d.%m.%Y} {qoil_i:10.3f} {qwat_i:10.3f} {bhp_mix_i:10.2f} {thp_i} 1 Hours {hours_i}\n" # output htab
        return (all_before_htab + recalculated_htab + all_after_htab, f"RECALCULATED,\tmax_wcut={max(wcut):.3f}\tgauge_md={gauge_md:.2f}\tgauge_tvdss={gauge_tvdss:.2f}")


def process_all_files():
    input_dir = sys.argv[1]
    out_dir = sys.argv[1]+"_out" 
    log_file = open("log_file.txt",'w')

    for root, dirs, files in os.walk(sys.argv[1]):
        new_structure = os.path.join(out_dir, root[len(input_dir)+1:])
        if not os.path.isdir(new_structure): 
            os.mkdir(new_structure)

        for item in files:
            input_file_name = os.path.join(root, item)
            out_file_content, out_log = read_WT_hist_file(input_file_name)
            out_file_name =  os.path.join(new_structure, item)
            #print(input_file_name)

            with open(out_file_name,'w') as out:
                #out.write(f"hello {out_file_name} ARRRGGGGHHH____REWRITEDDDDD_AGAIN!!!")
                out.write(out_file_content)
                log_file.write(f"{out_file_name} {out_log}\n")

    log_file.write(f"\n{datetime.now()}")
    log_file.close()

process_all_files()
#output, out_log = read_WT_hist_file(sys.argv[1])
#print(output)

# TODO smooth density change when well goes to PBU/from PBU  -  first variant done
# TODO find out how density influences the results of PI calculation!!
# TODO get TVDSS for current WT (BasPro) > partly DONE(needs check) > gives odd values with wrong MD-TVDSS for PLT-tests (need test filter in oracle-query)
        
