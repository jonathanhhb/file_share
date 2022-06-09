import argparse
from functools import reduce
import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def getChannels(jsonData):

    try:
        channelData = jsonData['Channels']
    except Exception as e:
        print("Didn't find 'Channels' in JSON data.")
        raise e

    return channelData


def getTraceName(channelTitle, keyValuePairs, primary):

    # trace name will have channel title and any property:value pairs
    # which aren't being grouped

    traceName = channelTitle + ':'

    for keyValuePair in keyValuePairs:
        (key, value) = keyValuePair.split(':')
        if key == primary:
            traceName = traceName + keyValuePair + ','

    traceName = traceName[:-1]  # remove the trailing ',' (or ':' if only channel title)

    return traceName


def indexFor(traceName, channels, traceKeys, normalize, overlay):

    if overlay:
        # all pools of the same channel overlaid
        index = 0
        for channel in channels:
            if channel in traceName:
                break
            index += 1
    else:
        # each trace separate
        index = traceKeys.index(traceName)

    # if we're normalizing, there's a normalized trace per regular trace
    if normalize:
        index *= 2

    # matplotlib is 1-based (like MATLAB)
    return index+1


def titleFor(traceName, channels, traceKeys, normalize, overlay):

    # use channel name
    if overlay:
        for channel in channels:
            if channel in traceName:
                title = channel
                break
    else:
        title = traceName

    return title


def accumulateTraceData(args, poolData, poolKeys):

    traceValues = {}
    normValues  = {}

    for channelName in args.channels:
        print(f"Processing channel '{channelName}'") if args.verbose else None

        for key in poolKeys:

            (channelTitle, keyValuePairs) = key.split(':',1)

            if channelTitle == channelName:
                print(f"Found channel '{channelName}' in pool data '{key}'") if args.verbose else None

                keyValuePairs = keyValuePairs.split(',')
                traceName = getTraceName(channelTitle, keyValuePairs, args.primary)
                traceData = np.array(poolData[ key ][ 'Data' ], dtype='float')
                normData  = np.array(poolData[ key.replace(channelTitle, args.by) ][ 'Data' ], dtype='float')

                if traceName not in traceValues:
                    print(f"New trace: '{traceName}'") if args.verbose else None
                    traceValues[traceName] = traceData
                    normValues[traceName]  = normData 
                else:
                    print(f"Add to trace: '{traceName}'") if args.verbose else None
                    traceValues[traceName] += traceData
                    normValues[traceName]  += normData 

    return (traceValues, normValues)


def plotTraces(args, traceValues, normValues):

    if len(traceValues) == 0:
        print("Didn't find requested channel(s) in property report.")
        return

    if not args.overlay:
        plotCount = len(traceValues)
    else:
        plotCount = len(args.channels)

    if args.normalize:
        plotCount *= 2

    plt.figure(args.filename, figsize=(20,11.25))
    traceKeys = sorted(traceValues.keys())
    print(traceKeys) if args.verbose else None

    if args.matrix:
        results = []
        for traceName in traceKeys:
            results.append(traceValues[traceName])
        cax = plt.imshow(results,interpolation='nearest')
        plt.xlabel('Time')
        plt.ylabel('Individual Properties')
        plt.yticks([])
        plt.colorbar(cax,orientation='horizontal')
    else:
        # plotting here
        for traceName in traceKeys:
            plotIndex = indexFor(traceName, args.channels, traceKeys, args.normalize, args.overlay)
            plt.subplot(plotCount, 1, plotIndex)
            plt.plot(traceValues[traceName], label=traceName)
            if args.normalize:
                plt.subplot(plotCount, 1, plotIndex+1)
                plt.ylim((0.0, 1.0))    # yes, this takes a tuple
                plt.plot(traceValues[traceName]/normValues[traceName], label=traceName)

        # make it pretty
        ax = plt.subplot(plotCount, 1, 1)
        for traceName in traceKeys:
            plotIndex = indexFor(traceName, args.channels, traceKeys, args.normalize, args.overlay)
            plotTitle = titleFor(traceName, args.channels, traceKeys, args.normalize, args.overlay)
            plt.subplot(plotCount, 1, plotIndex)
            plt.title(plotTitle)
            plt.legend() if args.legend else None
            if args.normalize:
                plt.subplot(plotCount, 1, plotIndex+1)
                plt.title(f"{plotTitle} normalized by {args.by}")
                plt.legend() if args.legend else None

    plt.tight_layout()

    if args.saveFigure:
        plt.savefig('propertyReport.png')

    plt.show()

    return


def main(args):

    jsonData    = readJsonFile(args.filename)
    poolData    = getChannels(jsonData)
    poolKeys    = sorted(poolData.keys())
    if args.verbose:
        print("Channels:Pools-")
        print(json.dumps(poolKeys, indent=4))

    if args.list:
        listChannelsAndIPs(poolData)
        return

    (traceValues, normValues) = accumulateTraceData(args, poolData, poolKeys)
    plotTraces(args, traceValues, normValues)

    return


def readJsonFile(filename):

    with Path(filename).open("r") as file:
        jsonData = json.load(file)

    return jsonData


def listChannelsAndIPs(channelKeys):

    channels = sorted(set([key.split(":",1)[0] for key in channelKeys]))    # keys look like "CHANNEL:IP:value,...,IP:value"

    print("\nChannels:")
    for channel in channels:
        print(f"\t{channel}")

    # Each channel _should_ have the same set of IPs, but we'll check them all
    csvkvps = [key.split(":",1)[1] for key in channelKeys]              # For each channel get a comma separated list of IP:value pairs (see format above)
    kvplists = [csv.split(",") for csv in csvkvps]                      # For each CSV convert to actual list by splitting on ","
    ips = [map(lambda t: t.split(":")[0], kvps) for kvps in kvplists]   # Convert each IP:value entry to just IP
    properties = sorted(reduce(lambda s, e: s.union(e), ips, set()))    # Add all IPs to an initially empty set

    print("\nIPs:")
    for property in properties:
        print(f"\t{property}")

    print()

    return


def processCommandline():

    parser = argparse.ArgumentParser(description='Property Report Plotting')
    parser.add_argument('filename', nargs='?', default='PropertyReport.json', help='property report filename [PropertyReport.json]')
    parser.add_argument('-c', '--channel', action='append', help='channel(s) to display [Infected]', metavar='channelName', dest='channels')
    parser.add_argument('-p', '--primary', help="Primary IP under which to roll up other IP keys and values")
    parser.add_argument('-n', '--normalize', help='plot channel(s) normalized by statistical population', action='store_true')
    parser.add_argument('-b', '--by', default="Statistical Population", help="Channel for normalization ['Statistical Population']")
    parser.add_argument('-o', '--overlay', help='overlay pools of the same channel', action='store_true')
    parser.add_argument('-s', '--save', help='save figure to disk', action='store_true', dest='saveFigure')
    parser.add_argument('-m', '--matrix', help='plot matrix for all properties', action='store_true')
    parser.add_argument('-v', '--verbose', action="store_true")
    parser.add_argument('--no-legend', action="store_false", dest="legend")     # Note args.legend default to True, passing --no-legend sets args.legend to False
    parser.add_argument('-l', '--list', action="store_true", help="List channels and IP keys found in the report. No plotting is performed with this option.")

    args = parser.parse_args()

    if not args.channels:
        args.channels = ['Infected']

    if not args.list:
        print(f"Filename:              '{args.filename}'")
        print(f"Channel(s):            {args.channels}")
        print(f"Primary:               {args.primary}")
        print(f"Normalize:             {args.normalize}")
        print(f"Normalization Channel: '{args.by}'") if args.normalize else None
        print(f"Overlay:               {args.overlay}")
        print(f"Save:                  {args.saveFigure}")
        print(f"Matrix:                {args.matrix}")

    return args


if __name__ == '__main__':
    args = processCommandline()
    main(args)
