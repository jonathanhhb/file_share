import os
from cgi import parse_qs, escape
from emod_api import peek_camp as pc
import site
import json


"""
1) Add a form that lets user fill out any/all fields of a CCDL-based event.
2) Render that back in the form for editing, plus render as CCDL.
3) Render as json.
4) Ingest a CCDL campaign, letting user select events to edit.
5) Render graphically.
"""

do_json = False

# This function will go into emod_api.
def params_to_ccdl( start_day, duration=None, reps=None, gap=None, nodes=None, frac=None, sex=None, minage=None, maxage=None, ips="*", signal=None, iv_name=None, payload=None, delay=None ):
    if signal == "None":
        signal = None
    if payload == "None":
        payload = None
    day = f"{start_day}"
    if reps and reps != "None":
        day += f"(x{reps}/_{gap})"
    elif duration and duration != "None" and duration != "-1.0":
        day += f"-{start_day+duration}"

    nodes = nodes
    #who = f"{frac}%"
    who = "STEERED" if type(frac) is str else f"{float(frac)*100}%"
    if "ale" in sex:
        who += f"/{sex}"
    if minage > 0:
        who += f"/>{minage}"
    if maxage < 125:
        who += f"/<{maxage}"
    if ips and ips != "" and ips != "None":
        who += f"/{ips}"

    if payload:
        iv_name = f"{iv_name}({payload})"
    else:
        iv_name = f"{iv_name}"
    if signal:
        iv_name = f"{signal}->{iv_name}"

    # Special code for Outbreaks to make the visualizer work better...
    #if "Outbreak" in iv_name:
        #iv_name += "+BroadcastEvent(NewInfection)+BroadcastEvent(Symptomatic)"

    ccdl = f"{day} :: {nodes} :: {who} :: {iv_name}"
    return ccdl

def application(environ, start_response):
    status = '200 OK'
    #output = b'Hooray, mod_wsgi is working'
    output = b"<html><head><link rel='stylesheet' href='minimal-table.css'></head><body><H1>CCDL Demo</H1>"
    # Process input...
    d = parse_qs( environ["QUERY_STRING"] )
    start = 1
    duration = None
    reps = None
    period = None

    where = "All"

    #who = "100%"
    coverage = "100%"
    sex = "Both"
    min_age = 0
    max_age = 125
    ips = ""

    # what = "NewInfection->SimpleVaccine(0.95)"
    trigger = "None" # will be from dropdown
    delay = "None"
    iv = "SimpleVaccine" # will be from dropdown
    iv_payload = "None"
    ccdl = None

    if len( d.keys() ) > 0:
        if "delete_id" in d.keys():
            # we are deleting a row of ccdl
            delete_id = int(d["delete_id"][0])
            with open( "/var/opt/idm/apache/camp.ccdl", "r" ) as ccdl_fp:
                ccdl_read = ccdl_fp.readlines()
            ccdl_read.pop( delete_id ) # delete a row
            with open( "/var/opt/idm/apache/camp.ccdl", "w" ) as ccdl_fp:
                for ccdl in ccdl_read:
                    ccdl_fp.write( ccdl.strip() )
                    ccdl_fp.write( "\n" )
            ccdl = None
        else:
            #when = d["when"][0]
            # when is either:
            # * Start_Day
            # * Start_Day-Stop_Day
            # * Start_Day(xreps/_period)
            #start=float(when.split(["-"][0].split("(")[0]))
            start=float(d["start"][0])
            if "duration" in d.keys() and d["duration"][0] != "None" and float(d["duration"][0]) != -1.0:
                duration=float(d["duration"][0])
            if "reps" in d.keys() and d["reps"][0] != "None" and d["reps"][0] != "1.0":
                reps=int(d["reps"][0])
            if "period" in d.keys() and d["period"][0] != "None":
                period=int(d["period"][0])

            where = d["where"][0]

            #who = d["who"][0]
            if "coverage" in d.keys():
                coverage =d["coverage"][0] 
                if "%" in coverage:
                    coverage = float(coverage.split( "%" )[0])/100.
                else:
                    coverage = float(coverage)
            if "sex" in d.keys():
                sex=d["sex"][0]
            if "min_age" in d.keys() and float(d["min_age"][0]) > 0:
                min_age=float(d["min_age"][0])
            if "max_age" in d.keys()and float(d["max_age"][0]) < 125:
                max_age=float(d["max_age"][0])
            if "ips" in d.keys():
                ips=d["ips"][0]

            #what = d["what"][0] 
            if "trigger" in d.keys() and d["trigger"][0] != "None":
                trigger=d["trigger"][0]
            if "delay" in d.keys():
                delay=d["delay"][0]
            if "iv" in d.keys():
                iv=d["iv"][0]
            if "iv_payload" in d.keys():
                iv_payload=d["iv_payload"][0]

            ccdl = params_to_ccdl( start_day=start, duration=duration, reps=reps, gap=period, nodes=where, frac=coverage, sex=sex, minage=min_age, maxage=max_age, ips=ips, signal=trigger, delay=delay, iv_name=iv, payload=iv_payload )
        # call emod_api.peek_campaign.encode_from_data( ccdl )

    output += f"""
        <H2>Editor</H2>
	<form action="/test_wsgi">
	  <label for="start"><b>When</b></label><br>
          <label for="start">Start_Day: </label>
	  <input type="text" id="start" name="start" value="{start}">
          <label for="duration">Duration (Opt): </label>
	  <input type="text" id="duration" name="duration" value="{duration}">
          <br>Repeats?
          
          <input type="checkbox" placeholder="Repeats" id="repeats" name="repeats" onclick="document.getElementById('reps_block').hidden=!document.getElementById('repeats').checked;" />

          <div id="reps_block" hidden=true >
              <label for="reps">Repetitions: </label>
              <input type="text" id="reps" name="reps" value="{reps}" size="4">
              <label for="period">Rep. Interval: </label>
              <input type="text" id="period" name="period" value="{period}" size="4">
          </div>

          <br><br>
	  <label for="where"><b>Where</b></label><br>
	  <input type="text" id="where" name="where" value={where}><br><br>

	  <label for="lname"><b>Who</b></label><br>
          <label for="coverage">Coverage: </label>
	  <input type="text" id="coverage" name="coverage" value={coverage}>
          <br><label for="sex">Targeted Sex (Opt): </label>
	  <select id="sex" name="sex" value={sex}>
              <option value="Both">Both</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
          </select>
          <br>Age Targeting?
          <input type="checkbox" id="age_range" name="age_range" onclick="document.getElementById('age_block').hidden=!document.getElementById('age_range').checked;" />
          <div id="age_block" hidden=true>
              <label for="min_age">Targeted Min Age: </label>
              <input type="text" id="min_age" name="min_age" value={min_age} size="4">
              <label for="max_age">Targeted Max Age: </label>
              <input type="text" id="max_age" name="max_age" value={max_age} size="4">
          </div><br>
          <label for="ips">Targeted Individual Properties (Opt): </label>
	  <input type="text" id="ips" name="ips" value={ips}><br><br>

	  <label for="lname"><b>What</b></label><br>
          <label for="trigger">Trigger (Opt): </label>
	  <input type="text" id="trigger" name="trigger" value={escape(trigger)}>
          <label for="trigger">Delay (Opt): </label>
	  <input type="text" id="delay" name="delay" value={escape(delay)}>
          <label for="trigger">Intervention: </label>
          """.encode( "ascii" )
    output += f"""
	  <select id="iv" name="iv" value={escape(iv)}>
              <option value="OutbreakIndividual">OutbreakIndividual</option>
              <option value="SimpleVaccine">SimpleVaccine</option>
              <option value="PropertyValueChanger">PropertyValueChanger</option>
              <option value="SimpleHealthSeekingBehavior">HealthSeekingBehavior</option>
              <option value="BroadcastEvent">BroadcastEvent</option>
              <option value="TBHIVConfigurableDrug">TBHIVConfigurableDrug</option>
              <option value="SimpleDiagnostic">GeneralDiagnostic</option>
              <option value="HIVRapidHIVDiagnostic">HIVDiagnostic</option>
              <option value="DiagnosticTreatNeg">TBDiagnostic</option>
              <option value="AntiMalarialDrug">AntiMalarialDrug</option>
          </select>
          <label for="trigger">Intervention Param (Context-Sensitive): </label>
          <input type="text" id="iv_payload" name="iv_payload" value={iv_payload}><br><br>
          <input type="submit" value="Submit">
        </form><hr>
        """.encode( "ascii" )
    output += "<H2>CCDL Format</H2>".encode( "ascii" )
    if ccdl:
        #output += ccdl.encode( "ascii" ) + "<hr>".encode( "ascii" )
        # Append new line to file on disk
        with open( "/var/opt/idm/apache/camp.ccdl", "a" ) as ccdl_fp: # does nothing!? :(
            ccdl_fp.write( ccdl.strip() )
            ccdl_fp.write( "\n" )

        # Read in new file
    if os.path.exists( "/var/opt/idm/apache/camp.ccdl" ):
        with open( "/var/opt/idm/apache/camp.ccdl", "r" ) as ccdl_fp: # does nothing!? :(
            ccdl_read = ccdl_fp.readlines()
        #output += "<form action='/test_wsgi'>".encode( "ascii" )
        output += "<table><tr><th></th><th>When?</th><th>Where?</th><th>Who?</th><th>What?</th></tr><tr>".encode( "ascii" )
        row = 0
        for ccdl_line in ccdl_read:
            if len( ccdl_line.strip() ) > 0:
                output += f"<td><form id='row{row}'><input type='hidden' name='delete_id' value='{row}'/></form></td><td>".encode( "ascii" )
                output += ccdl_line.replace( "::", "</td><td>" ).encode( "ascii" ) 
                output += f"""
                    </td><td><input form='row{row}' type='Submit' value='Delete'></td></tr>"
                """.encode( "ascii" )
                row += 1
        output += "</tr></table>".encode( "ascii" )
        #output += "</form>".encode( "ascii" )
        output += "<hr>".encode( "ascii" )

        # Create campaign.json
        if do_json:
            import emod_api.campaign as camp
            from emodpy_hiv.camp_creator import create_campaign_from_concise as ccfc
            outfile = "/var/opt/idm/test_campaign.json"
            camp.set_schema( "/var/www/html/schema.json" )
            camp.unsafe = True
            ccfc( "/var/opt/idm/apache/camp.ccdl", outfile=outfile )

            with open( outfile, "r" ) as camp_json_fp:
                camp_json = json.load( camp_json_fp )
                output += """
                JSON?<input type="checkbox" id="json" name="json" onclick="document.getElementById('json_block').hidden=!document.getElementById('json').checked;" />
                """.encode( "ascii" )
                output += '<div id="json_block" hidden=true >'.encode( "ascii" )
                output += "<H2>JSON Format</H2>".encode( "ascii" )
                output += "<pre>".encode( "ascii" ) + json.dumps( camp_json, indent=4, sort_keys=True ).encode( "ascii" ) + "</pre>".encode( "ascii" )
                output += "</div>".encode( "ascii" )

        import emod_api.interventions.ccdl_viz as viz
        result = viz.viz( "/var/opt/idm/apache/camp.ccdl", out_name="/var/opt/idm/apache/camp.sv" )
        #viz.viz( "/var/opt/idm/apache/camp.ccdl", out_name="/var/www/html/camp.sv" )

        #output += "<hr><H2>GRAPH</H2><img src='/var/opt/idm/apache/camp.sv.gv.png'>".encode( "ascii" )
        output += "<hr><H2>GRAPH</H2><img src='camp.sv.png' width='1000'>".encode( "ascii" )

    output += f"<hr>DEBUG: {site.getsitepackages()}".encode( "ascii" )
    output += f"\nDEBUG: {os.getcwd()}".encode( "ascii" )
    #output += f"\nDEBUG: {result}".encode( "ascii" )
    output += """
        </body>
	</html>
    """.encode( "ascii" )
 
    response_headers = [('Content-type', 'text/html'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)
 

    return [output]
