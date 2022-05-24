#!/usr/bin/env python


resampled_data = {}
agebins = [ "LESS_1", "LESS_5", "LESS_10", "LESS_15", "LESS_20", "LESS_25", "LESS_30", "LESS_35", "LESS_40", "LESS_45", "LESS_50", "LESS_55", "LESS_60", "LESS_65", "LESS_70", "LESS_75", "LESS_80", "LESS_85", "LESS_90", "LESS_95", "GREAT_95" ]
datacols = set()
header = None
def get_orig_file( path_to_file ):
    with open( path_to_file, "r" ) as fp:
        data = fp.readlines()
    return data


def convert_year_float_to_date( input_filename, input_data ):
    import datetime
    base_date=datetime.datetime( year=1850, month=1, day=1 )
    new_file = []
    global header
    for line in input_data:
        raw_year = line.split(",")[0]
        #if raw_year.isascii():
        if raw_year == "Year":
            header = line
            continue
        new_time = base_date + datetime.timedelta( float(raw_year.strip())*365 )
        #print( new_time.strftime( "%Y/%m/%d" ) )
        new_year=new_time.strftime( "%Y/%m/%d" )
        new_line = new_year + "," + ",".join( line.split(",")[1:] )
        new_file.append( new_line )

    output_filename = input_filename+".new"
    with open( output_filename, "w" ) as fp:
        fp.write( header )
        for line in new_file:
            fp.write( line )
    return output_filename 

def resample( intermediate_filepath ):
    import pandas as pd
    import json
    import numpy as np
    df = pd.read_csv( intermediate_filepath, header=0, sep='\s*,\s*', parse_dates=['Year'])
    for node in [ 1, 2 ]:
        if node not in resampled_data.keys():
            resampled_data[str(node)] = {}
        for age_bin in agebins:
            if age_bin not in resampled_data[str(node)]:
                resampled_data[str(node)][age_bin] = {}
            node_age_data=df.query(f"NodeID=={node}").query( f"AgeBin=='{age_bin}'" )
            #col = 'Population'
            for col in node_age_data.keys():
                if col in [ "Year", "NodeID", "AgeBin" ]:
                    continue
                datacols.add( col )
                ts = pd.Series(node_age_data[col].values, index=node_age_data['Year'])
                if "New" in col or col.startswith( "Inc" ):
                    def amortize( ts ):
                        intermed = ts.resample( "M" ).sum()
                        last_left = 0
                        group_size = 1
                        # now amortize original values across zeros
                        for i in range( len( intermed ) ):
                            if intermed.values[i] == 0:
                                group_size += 1
                                continue
                            else:
                                # hack to work around long sections of actual 0s
                                if group_size>12:
                                    last_left+=(group_size-12)
                                    group_size = 12
                                cum = intermed.values[i]
                                amortized_value = float(cum)/group_size
                                #print( f"Setting {group_size} elements of col {col} node {node} age {age_bin} block indexed at {last_left} to {amortized_value}." )
                                for j in range(group_size):
                                    intermed.values[last_left+j] = amortized_value 
                                last_left += group_size
                                group_size = 1
                        return intermed
                    intermed = amortize( ts )
                    def custom_resampler( arraylike ):
                        # Idea here is to fill in the new values with the original value divided by the length. No idea if this works
                        # This does not work in any way that isn't totally useless, at least for upsampling.
                        return np.sum(arraylike)/len(arraylike)
                    #print( f"Resampling col {col} node {node} age {age_bin}." )
                    #intermed = ts.resample( "M" ).apply( custom_resampler )
                    resamp = intermed.resample("Y").sum()
                else:
                    #resamp = ts.resample("Y").ffill().interpolate()
                    resamp = ts.resample("D",origin="1850-01-01").interpolate(method="linear").resample("Y").asfreq()

                #resampled_data[age_bin][node][col] = list(resamp)
                resampled_data[str(node)][age_bin][col] = [ i[1] for i in resamp.iteritems() ]
        dates = [ i[0].strftime('%Y-%m-%d') for i in resamp.iteritems() ] # TBD: do this once
    resampled_data['Dates']=dates
    #print( json.dumps( resampled_data, indent=4, sort_keys=True ) )
    with open( "resamp.json", "w") as fp:
        fp.write( json.dumps( resampled_data, indent=4, sort_keys=True ) )
    return resampled_data

def json2csv( resampled_json, final_csv ):
    with open( final_csv, "w") as fp:
        fp.write( header )
        for t in range(len(resampled_json[ "Dates"] )):
            for node in resampled_json.keys():
                if node=="Dates":
                    continue
                for agebin in agebins:
                    colrow = ",".join( [ f"{resampled_json[ node ][ agebin ][ col ][ t ]}" for col in resampled_json[ node ][ agebin ].keys() ] )
                    row = f"{resampled_json['Dates'][t]},{node},{agebin}," + colrow + "\n"
                    fp.write( row )
                    #print( row )


import sys
print( "Loading file." )
data = get_orig_file( sys.argv[1] )
print( "Converting year." )
new_filename = convert_year_float_to_date( sys.argv[1], data )
print( "Resampling." )
resampled_json = resample( new_filename )
print( "Writing csv." )
final_csv = json2csv( resampled_json, sys.argv[1].replace( "ByAge", "ByAge_resampled" ) )
