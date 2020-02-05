import sys
from datetime import datetime, timedelta

DOIL=0.814
DWAT=1.059
REF =2434
NULL = 0.01



def get_gauge_tvdss_from_db_output(well_name, approximate_date): 
    #f_date = '14.05.2019'
    #f_well = 'WQ2-178'
    with open('wt_gauges_MD_TVDSS', 'r') as gauge_db: # DBout filename hardcoded !!
        lines = [ [abs(datetime.strptime(y.split()[1],"%d.%m.%Y")-datetime.strptime(approximate_date,"%d.%m.%Y")), y.split()[0], y.split()[3], y.split()[4]] for y in [x.strip() for x in gauge_db] if y.split()[0]==well_name] 
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
    oil, water, wcut, gauge_tvdss, press_mix = 0, 0, 0, 0, 0
    prev_press, prev_date_time = 0, datetime(year=1900, month=1, day=1)
    dmix = DOIL
    prev_dmix = DOIL

    with open(file_name,'r') as input_file:
        lines = [x.strip() for x in input_file]
        #filter_lines = [x for x in lines[lines.index('HTAB')+1:lines.index('ENDH')] if x[0:2]!='--']
        
        #well_type = lambda orat, wrat : 'Water injector' if orat+wrat==wrat else 'Oil producer' if orat>0 else 'Undefined' 

        is_htab=False
        regime_changed = False

        for x in lines: 
            if x == 'ENDH': 
                is_htab=False


            if is_htab and x[0:2]!='--': 
                words = x.split()
                gauge_tvdss = get_gauge_tvdss_from_db_output(words[0], words[1])

                oil, water, press_oil = float(words[2]), float(words[3]), float(words[4])
                date_time = datetime.strptime(words[1], "%d.%m.%Y") + timedelta(hours=float(words[8]))
                wcut =  water/(oil+water)
                regime_changed = (oil+water)== (p_oil+p_water)

                dP = derivative(prev_press, press_oil, prev_date_time, date_time)
                dmix = (wcut*DWAT+(1-wcut)*DOIL)

                if press_oil > NULL:
                    press_mix = press_oil+(REF-gauge_tvdss)*9.81*(dmix-DOIL)/100
                else: 
                    press_mix = press_oil



                #print(f"{wcut:.2f} {gauge_tvdss:.1f} {press_mix:.3f} {x}") # debug
                print(f"{derivative(prev_press, press_oil, prev_date_time, date_time)} {wcut} {x}") # debug
                #print(*words[0:4], press_mix, *words[5:])

                prev_press  = press_oil
                prev_date_time = date_time
                prev_dmix = dmix
            else:
                #print(x) # print other lines
                pass
            

            if x == 'HTAB': 
                is_htab=True



read_WT_hist_file(sys.argv[1])

# TODO get TVDSS for current WT (BasPro) 
#     partly DONE(needs check)
#     unloads odd values with wrong MD-TVDSS for PLT-tests (need test filter in oracle-query)
#
        
