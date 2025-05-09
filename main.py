import requests
import pandas as pd
import time
import datetime
import json
from os import getcwd, mkdir, listdir
from os.path import isdir

OUTPUT_FILE_NAME = "time_splits.csv"
RIDES_FILE_PATH = "epp_data.csv"

ERRORS_FILE_NAME = "errors.txt"
API_KEY_FILE_NAME = "api-key.txt"
ARCHIVE_DIR = "2023_archive"
API_CALL_RATE = 25 #per second
NEW_DATA = False #set this to true the first time the script is run to create an archive of API call results

DATA_TZ = -5 #offset relative to UTC in hours, do not change this
LOCAL_TZ = -6 #necessary as mktime utilizes system time zone for conversion to epoch time, set this to the UTC offset of your timezone
TARGET_WEEK = "2/13/2025"

def retrieve_api_key(file_name: str) -> str:
    """Retrieves the contents of the specified file."""
    api_key = ""
    with open(file_name, "r") as file:
        api_key = file.read()

    assert api_key != ""

    return api_key

def construct_request(ride_data: dict, api_key: str) -> str:
    """Creates the request used to retrieve route recommendations from Google."""
    output_format = "json"
    endpoints = encode_endpoints(ride_data["Start"], ride_data["End"])
    mode = "mode=transit"
    departure_time = "departure_time=" + str(ride_data["Request Time"])

    request_url = f"https://maps.googleapis.com/maps/api/directions/"
    request_url += f"{output_format}?{endpoints}&key={api_key}&{mode}&{departure_time}"

    return request_url

def encode_endpoints (start_coords: tuple, end_coords: tuple) -> str :
    """Formats coordinates for inclusion in request url."""
    origin = f"origin={start_coords[0]},{start_coords[1]}"
    destination = f"destination={end_coords[0]},{end_coords[1]}"

    return f"{origin}&{destination}"


def retrieve_coords(df: pd.core.frame.DataFrame, i:int) -> tuple:
    """Retrieve start & end coordinates from EPP data file."""
    start_lat = df.iloc[i]["Pickup Latitude"]
    start_long = df.iloc[i]["Pickup Longitude"]
    end_lat = df.iloc[i]["Drop Off Latitude"]
    end_long = df.iloc[i]["Drop Off Longitude"]

    route_data = ((start_lat, start_long), (end_lat,end_long))
    return route_data


def pool_data(rides: list):
    """Pool data into dictionary format to construct final dataframe."""
    ids = []
    start_lats = []
    start_longs = []
    end_lats = []
    end_longs = []
    durations = []

    for ride in rides:
        if "Transit Duration" in ride:
            ids.append(ride["ID"])
            start_lats.append(ride["Start"][0])
            start_longs.append(ride["Start"][1])
            end_lats.append(ride["End"][0])
            end_longs.append(ride["End"][1])
            durations.append(ride["Transit Duration"])

    df_input = {"ID": ids,
                "Pickup Latitude": start_lats,
                "Pickup Longitude": start_longs,
                "Drop Off Latitude": end_lats,
                "Drop Off Longitude": end_longs,
                "Transit Duration": durations}

    duration_df = pd.DataFrame(df_input)

    return duration_df


def execute_all_api_calls(all_rides, api_key):
    """Retrieves quickest public transportation directions from Google API. Result is archived on machine."""
    cwd = getcwd()
    exising_jsons = listdir(cwd + "\\" + ARCHIVE_DIR)
    archived_ids = [int(file_name.removesuffix(".json")) for file_name in exising_jsons]

    for ride in all_rides:
        if ride["ID"] in archived_ids:
            print("ID", ride["ID"], "skipped.")
            continue

        time.sleep(1 / API_CALL_RATE)

        request_url = construct_request(ride, api_key)
        transit_route = requests.get(request_url)

        if ride["Start"] == ride["End"]:
            print("Bad coordinates at ID:", ride["ID"])
            with open(ERRORS_FILE_NAME, "a+") as file:
                file.write("Bad coordinates at ID:" + str(ride["ID"]) + '\n')
                file.write(request_url + '\n')

        else:
            request_json = transit_route.json()
            archive_api_call_results(request_json, ride["ID"])

            try:
                if "DRIVING" not in get_travel_modes(request_json): #ensures no driving directions were given
                    duration = request_json["routes"][0]["legs"][0]["duration"]["text"]
                    print(str(ride["ID"]) + ":", duration)

                else:
                    print("Route:", ride["ID"], "was provided driving directions.")
                    with open(ERRORS_FILE_NAME, "a+") as file:
                        file.write("Route " + str(ride["ID"]) + " was provided driving directions.\n")
                        file.write(request_url + '\n')

            except:
                print("No route at ID:", ride["ID"])
                with open(ERRORS_FILE_NAME, "a+") as file:
                    file.write("No route at ID:" + str(ride["ID"]) + '\n')
                    file.write(request_url + '\n')


def add_transit_durations(rides) -> list:
    """Goes through all archived API calls. Retrieves public transit duration from all successful calls."""
    archive_path = getcwd() + "\\archive"
    file_names = listdir(archive_path)
    ids = [int(file_name.removesuffix(".json")) for file_name in file_names]

    for ride in rides:
        if ride["ID"] % 100 == 0:
            print("Ride", ride["ID"], "processed.")

        if ride["ID"] in ids:

            with open(archive_path+ "\\" + str(ride["ID"]) + ".json", 'r') as file:
                api_call_results = json.load(file)

            #these skip archived results that do not provide public transit direction
            if api_call_results["status"] == "ZERO_RESULTS": #this occurs when Google could not find a reasonable connecting route
                continue

            travel_modes = get_travel_modes(api_call_results)
            if "DRIVING" in travel_modes:  # ensures no driving directions were given
                print("Driving route detected: " + str(ride["ID"]))
                continue

            if "TRANSIT" in travel_modes: #public transit directions
                arrival_time = api_call_results["routes"][0]["legs"][0]["arrival_time"]["value"]
                request_time = ride["Request Time"]
                duration = int((arrival_time - request_time) / 60)

            else: #walking directions
                duration = int(api_call_results["routes"][0]["legs"][0]["duration"]["value"] / 60)

            ride["Transit Duration"] = duration
            ride["Travel Mode"] = travel_modes

    return rides


def retrieve_transit_durations(api_call_results, travel_modes) -> int:
    """Opens archived API call to retrieves transit duration."""
    if "TRANSIT" in travel_modes: #public transit directions
        arrival_time = api_call_results["routes"][0]["legs"][0]["arrival_time"]["value"]
        request_time = ride["Request Time"]
        duration = int((arrival_time - request_time) / 60)

    else: #walking directions
        duration = int(api_call_results["routes"][0]["legs"][0]["duration"]["value"] / 60)

    return duration

def archive_api_call_results(result_json: dict, route_id: int):
    """Archives results of api calls for future reference."""
    path = getcwd() + "\\" + ARCHIVE_DIR
    if not isdir(path): # check for existence of archive folder, if it does not exist create it
        mkdir(path)

    serialized_json = json.dumps(result_json, indent=4)
    with open(f"{path}\\{route_id}.json", "w+") as file:
        file.write(serialized_json)


def load_json_by_id(ride_id: int) -> dict:
    path = getcwd() + '\\' + ARCHIVE_DIR + f"\\{ride_id}.json"
    with open(path, 'r') as file:
        api_call_results = json.load(file)
    return api_call_results


def get_travel_modes(request_json):
    """Determines all travel modes used for a specific route."""
    directions = request_json["routes"][0]["legs"][0]["steps"]
    travel_modes = {step["travel_mode"] for step in directions}

    return travel_modes


def extract_travel_by_mode(route_id):
    """Sums time and distance per travel mode in each route."""
    api_call_results = load_json_by_id(route_id)
    segments = api_call_results["routes"][0]["legs"][0]["steps"] #zone in on portion of json holding related info
    data = {travel_mode: {"DISTANCE": 0, "TIME":0} for travel_mode in get_travel_modes(api_call_results)} #create base structure for holding data

    for segment in segments:
        travel_mode = segment["travel_mode"]
        distance = segment["distance"]["value"]
        travel_time = segment["duration"]["value"]

        data[travel_mode]["DISTANCE"] += distance
        data[travel_mode]["TIME"] += travel_time

    #data clean up and unit conversion
    for travel_mode in data:
        data[travel_mode]["DISTANCE"] = data[travel_mode]["DISTANCE"] / 1609.34  #meters to miles
        data[travel_mode]["TIME"] = int(data[travel_mode]["TIME"] / 60 ) #seconds to minutes

    return data


def clean_date_data(date_str: str) -> str:
    """Formats data to be compatible with formatting options available to python's time library."""
    split_date = date_str.split('/')
    for i in range(len(split_date)):
        if len(split_date[i]) == 1:
            split_date[i] = '0' + split_date[i] #formatting requires double-digit entries for days & months

    fixed_date = '/'.join(split_date)

    return fixed_date


def clean_time_data(time_str: str) -> str:
    """Formats data to be compatible with formatting options available to python's time library."""
    if len(time_str) == 6:
        time_str = '0' + time_str #double-digit formatting is required for minutes and hours

    return time_str


def retrieve_request_time(df: pd.core.frame.DataFrame, i:int) -> int:
    """Construct unix time from time recording in main data file."""
    request_date = clean_date_data(df.iloc[i]["Request Date (Local)"])
    request_time = clean_time_data(df.iloc[i]["Request Time (Local)"])
    unix_time = calculate_epoch_time(request_date, request_time)
    return unix_time


def retrieve_drop_off_time(df: pd.core.frame.DataFrame, i:int) -> int:
    """Construct unix time from time recording in main data file."""
    request_date = clean_date_data(df.iloc[i]["Drop-off Date (Local)"])
    request_time = clean_time_data(df.iloc[i]["Drop-off Time (Local)"])
    unix_time = calculate_epoch_time(request_date, request_time)
    return unix_time


def calculate_epoch_time(date_str, time_str)->int:
    """Determines seconds since start of epoch based on local time entry."""
    # convert date info into struct_time object
    date_format = "%m/%d/%Y"
    date_struct = time.strptime(date_str, date_format)  # documentation https://docs.python.org/3.12/library/datetime.html#strftime-and-strptime-behavior

    # convert time info into struct_time object
    time_format = "%I:%M%p"
    time_struct = time.strptime(time_str, time_format)

    #combined into a single struct_time object
    input_tuple = (date_struct.tm_year, #year
                   date_struct.tm_mon, #month
                   date_struct.tm_mday, #day
                   time_struct.tm_hour + (LOCAL_TZ - DATA_TZ) if time_struct.tm_hour + (LOCAL_TZ - DATA_TZ) < 24 else 0, #hour
                   time_struct.tm_min, #minute
                   time_struct.tm_sec, #second
                   date_struct.tm_wday, #day of week
                   date_struct.tm_yday, #day of year
                   date_struct.tm_isdst) #daylight savings flag

    combined_struct = time.struct_time(input_tuple)
    epoch_time = time.mktime(combined_struct) #convert struct_time object into num of seconds since 1970

    return int(epoch_time) #google api requires whole numbers


def massage_time(source_unix_time:int, target_week_unix:int) -> int:
    """Takes the time retrieved from the data and aligns it with the specified week.

     The accepted range for the Directions API is ~ -7days to +3 months."""
    source_time_tuple = time.localtime(source_unix_time)
    source_day_of_the_week = source_time_tuple.tm_wday #tuple format is used to extract and match days of the week

    target_time_tuple = time.localtime(target_week_unix)
    target_day_of_the_week = target_time_tuple.tm_wday # 0 is Monday, 7 is Sunday

    one_day_delta = datetime.timedelta(days=1) # time delta class used to auto handle changes in days, months, years, ect


    target_week_datetime = datetime.date.fromtimestamp(target_week_unix) # time class compatible with time delta class
    new_day = target_week_datetime + one_day_delta * (source_day_of_the_week - target_day_of_the_week)
    new_tuple = new_day.timetuple()

    combined_tuple = (new_tuple.tm_year, #year
                      new_tuple.tm_mon,  # month
                      new_tuple.tm_mday,  # day
                      source_time_tuple.tm_hour,  # hour
                      source_time_tuple.tm_min,  # minute
                      source_time_tuple.tm_sec,  # second
                      new_tuple.tm_wday,  # day of week
                      new_tuple.tm_yday,  # day of year
                      new_tuple.tm_isdst)  # daylight savings flag

    combined_unix = int(time.mktime(combined_tuple))

    return combined_unix


def military_time_from_unix(unix_time:int) -> str:
    """Turns unix time back into a human-readable time, while accounting for timezone changes."""
    time_struct = time.localtime(unix_time)
    time_hour = time_struct.tm_hour + (DATA_TZ - LOCAL_TZ) if time_struct.tm_hour + (DATA_TZ - LOCAL_TZ) < 24 else 0
    time_min = time_struct.tm_min
    military_time = str(time_hour) + ":" + str(time_min)
    return military_time

#################### UTILITIES ####################
#misc functions used for debugging & testing

def construct_api_call_for_id(ride_id: int) -> str:
    """Creates the html address used to make the call for a specific ride."""
    api_key = retrieve_api_key(API_KEY_FILE_NAME)
    ride_data = {}
    ride_data["Start"], ride_data["End"] = retrieve_coords(eppDF, ride_id)

    original_unix_time = retrieve_request_time(eppDF, ride_id)
    target_unix_time = calculate_epoch_time(TARGET_WEEK,"5:00PM")  # time_str here is not used. Only provided to fulfill argument requirements.
    in_zone_time = massage_time(original_unix_time, target_unix_time)
    ride_data["Request Time"] = in_zone_time

    api_call_html = construct_request(ride_data, api_key)
    return api_call_html

def generate_mode_counts() -> dict:
    """Counts the number of routes utilizing each combination of transportation options."""
    archive_path = getcwd() + "\\archive"
    file_names = listdir(archive_path)
    ids = [int(file_name.removesuffix(".json")) for file_name in file_names]

    travel_counts = {}
    for id_ in ids:
        api_call_results = load_json_by_id(id_)

        # these skip archived results that do not provide public transit direction
        if api_call_results[
            "status"] == "ZERO_RESULTS":  # this occurs when Google could not find a reasonable connecting route
            continue
        if "DRIVING" in get_travel_modes(api_call_results):  # ensures no driving directions were given
            continue

        travel_modes = tuple(get_travel_modes(api_call_results))
        if not travel_modes in travel_counts:
            travel_counts[travel_modes] = 1
        else:
            travel_counts[travel_modes] += 1

    return travel_counts

###################################################




if __name__ == "__main__":
    api_key = retrieve_api_key(API_KEY_FILE_NAME)
    eppDF = pd.read_csv(RIDES_FILE_PATH)
    print(construct_api_call_for_id(10))

    #retrieve data from file
    data = []
    for i in range(eppDF.shape[0]): #loops through all rows in source data
        ride = {}
        ride["ID"] = i
        ride["Start"], ride["End"] = retrieve_coords(eppDF, i)
        ride["Request Time"] = retrieve_request_time(eppDF, i)
        ride["Drop-off Time"] = retrieve_drop_off_time(eppDF, i)
        ride["Ride Share - Total Time"] =  ride["Drop-off Time"] - ride["Request Time"]

        data.append(ride)

    #moves historic times into the window of API calculation
    for ride in data:
        original_unix_time = ride["Request Time"]
        target_unix_time = calculate_epoch_time(TARGET_WEEK, "5:00PM")  # time_str here is not used. Only provided to fulfill argument requirements.
        in_zone_time = massage_time(original_unix_time, target_unix_time)
        ride["Request Time"] = in_zone_time

    #construct and execute API calls
    if NEW_DATA:
        execute_all_api_calls(data, api_key)

    #process api call data
    archive_path = getcwd() + '\\' + ARCHIVE_DIR
    file_names = listdir(archive_path)
    ids = [int(file_name.removesuffix(".json")) for file_name in file_names]

    for ride in data:
        if ride["ID"] % 100 == 0:
            print("Ride", ride["ID"], "processed.")

        if ride["ID"] in ids:
            api_call_results = load_json_by_id(ride["ID"])
            # these skip archived results that do not provide public transit direction
            if api_call_results["status"] in ["ZERO_RESULTS", "UNKNOWN_ERROR"]:  # this occurs when Google could not find a reasonable connecting route
                continue

            travel_modes = get_travel_modes(api_call_results)

            duration = retrieve_transit_durations(api_call_results, travel_modes)
            ride["Transit Duration"] = duration
            ride["Travel Mode"] = travel_modes

    #construction & recording of final dataset
    transit_duration_df = pool_data(data)

    #temporary time
    hour_column = []
    for ride in data:
        if "Transit Duration" in ride: #only present if API call was successful in creating public transportation directions
            hour = int(military_time_from_unix(ride["Request Time"]).split(":")[0])
            hour_column.append(hour)
    transit_duration_df["Hour"] = hour_column

    #epp to public transit ratio
    # eppDurations = eppDF[["ID", "Total Time (min)"]]
    # publicTransitDurations = transit_duration_df[["ID", "Transit Duration"]]
    # mergedDF = pd.merge(eppDurations, publicTransitDurations, on="ID")
    # mergedDF["Ratio"] = mergedDF["Transit Duration"] / mergedDF["Total Time (min)"]
    # transit_duration_df["Duration Ratio"] = mergedDF["Ratio"]

    #time splits
    walking_times = [extract_travel_by_mode(int(route["ID"]))["WALKING"]["TIME"] for i, route in transit_duration_df.iterrows()]
    transit_duration_df["Time Spent - Walking"] = walking_times

    bus_times = []
    for i, route in transit_duration_df.iterrows():
        time_split = extract_travel_by_mode(int(route["ID"]))
        if "TRANSIT" in time_split:
            bus_times.append(time_split["TRANSIT"]["TIME"])
        else:
            bus_times.append(0)

    transit_duration_df["Time Spent - Bus"] = bus_times

    transit_duration_df["Time Spent - Waiting"] = transit_duration_df["Transit Duration"] - (transit_duration_df["Time Spent - Bus"] + transit_duration_df["Time Spent - Walking"])

    #file creation
    walkingTimesDF = transit_duration_df[ ["ID", "Pickup Latitude", "Pickup Longitude", "Transit Duration", "Hour", "Time Spent - Walking"]]
    busTimesDF = transit_duration_df[ ["ID", "Pickup Latitude", "Pickup Longitude", "Transit Duration", "Hour", "Time Spent - Bus"]]
    waitingTimesDF = transit_duration_df[ ["ID", "Pickup Latitude", "Pickup Longitude", "Transit Duration", "Hour", "Time Spent - Waiting"]]
    allTimesDF = transit_duration_df[ ["ID", "Pickup Latitude", "Pickup Longitude", "Transit Duration", "Hour", "Time Spent - Bus", "Time Spent - Walking", "Time Spent - Waiting"]]

    walkingTimesDF.to_csv(OUTPUT_FILE_NAME + "Walking.csv")
    busTimesDF.to_csv(OUTPUT_FILE_NAME + "Public Transit.csv")
    waitingTimesDF.to_csv(OUTPUT_FILE_NAME + "Waiting.csv")
    allTimesDF.to_csv(OUTPUT_FILE_NAME)
