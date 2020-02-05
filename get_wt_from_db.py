import cx_Oracle
import datetime

SDATE = '01.01.2014'
FDATE = '01.01.2020'

#p.PRESZAB,     
#GDR_RATE.RFLUID, 
#p.NRES 
#join GDR_RATE on GDR_RATE.IDWELL = p.IDWELL and GDR_RATE.DTBGN = p.DTBGN and GDR_RATE.NRES = p.NRES)

pbu_query_raw = f"""
select 
    WELLNAME,
    DTBGN,
    DPDEVICE,
    (TVDSS-(MD - DPDEVICE)*(cos(INKL/57.2958))) as TVDDEVICE
from(
                select  
                    p.IDWELL                            as IDWELL, 
                    BASP_REGISTRYWELL.WELLNAME          as WELLNAME,
                    p.DTBGN                             as DTBGN, 
                    GDR_TEST.DPDEVICE                   as DPDEVICE,
                    itb.MD                              as MD,
                    itb.TVDSS                           as TVDSS,
                    itb.INKL                            as INKL,
                    itb.AZIM                            as AZIM,
                    row_number() over(partition by p.IDWELL, p.DTBGN order by abs(itb.MD-GDR_TEST.DPDEVICE) asc) as RN
                from GDR_MSRPRESS p  
                join GDR_TEST on GDR_TEST.IDWELL = p.IDWELL and GDR_TEST.DTBGN = p.DTBGN and GDR_TEST.NRES = p.NRES  
                join BASP_REGISTRYWELL on BASP_REGISTRYWELL.IDWELL = p.IDWELL

                join (select 
                           RSRC_REGISTRYINKL.IDWELL as IDWELL,
                           i.DPTINKL as MD, 
                           i.AGLINKL as INKL, 
                           i.AZMINKL as AZIM, 
                           i.AOINKL  as TVDSS
                      from RSRC_INKL i 
                      JOIN RSRC_REGISTRYINKL ON i.IDINKL = RSRC_REGISTRYINKL.IDINKL
                      order by RSRC_REGISTRYINKL.IDWELL, i.DPTINKL) itb
                on itb.IDWELL=p.IDWELL and itb.MD > GDR_TEST.DPDEVICE
                where p.DTBGN > TO_DATE('{SDATE}','DD.MM.YYYY') 
                order by p.DTBGN, p.IDWELL
                ) 
                where RN = 1
                order by IDWELL, DTBGN

                """ # PBU press


def get_data_from_database_cns(connection, query_string, delimiter = ';'):
    with connection.cursor() as cur:
        cur.execute(query_string)
        [print(x[0], end=delimiter) for x in cur.description] # print table headers
        print()
        for result in cur:
            #print(result)
            for w in result:
                if w == None:
                    print("",end = delimiter)
                elif isinstance(w, datetime.datetime):
                    print(f"{w:%d.%m.%Y %H:%M:%S}",end = delimiter)
                else:
                    print(f"{w}",end = delimiter)
            print()

def connect_database():
    host_name = '10.201.194.37'
    port_number = 1521
    service_name = 'WQ2'
    user = 'WQ2_RO'
    password = user
    dsn_tns = cx_Oracle.makedsn(host_name, port_number, service_name)
    return cx_Oracle.connect(user, password, dsn_tns)

def connect_and_query():
    connection = connect_database()  #print(connection.version)
    get_data_from_database_cns(connection, pbu_query_raw,' ') # 
    connection.close()

connect_and_query()
