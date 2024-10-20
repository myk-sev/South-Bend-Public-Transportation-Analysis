import requests
import pandas as pd
import time
import datetime
import json
from os import getcwd, mkdir, listdir
from os.path import isdir

PROGRESS_FILE_NAME = "temp_transit_duration.csv"
RIDES_FILE_NAME = "EPP_Uber_Rides_2024.csv"
ERRORS_FILE_NAME = "errors.txt"
API_KEY_FILE_NAME = "api-key.txt"
API_CALL_RATE = 25 #per second
NEW_DATA = False #set this to true if this script is being executed on a data set for the first time

DATA_TZ = -5 #offset relative to UTC in hours
LOCAL_TZ = -6 #necessary as mktime utilizes system time zone for conversion to epoch time
TARGET_WEEK = "11/06/2024"

### Test Routes ###
HOME_TO_SCHOOL = {"Start": (41.525,-87.507), "End": (41.555,-87.335), "Request Time": int(time.time())}
EPP_EXAMPLE = {"Start": (41.691,-86.181), "End": (41.704,-86.236), "Request Time": int(time.time())}
###################

def encode_endpoints (start_coords: tuple, end_coords: tuple) -> str :
    """Formats coordinates for inclusion in request url."""
    origin = f"origin={start_coords[0]},{start_coords[1]}"
    destination = f"destination={end_coords[0]},{end_coords[1]}"

    return f"{origin}&{destination}"


def construct_request(ride_data: dict, api_key: str) -> str:
    """Creates the request used to retrieve route recommendations from Google."""
    output_format = "json"
    endpoints = encode_endpoints(ride_data["Start"], ride_data["End"])
    mode = "mode=transit"
    departure_time = "departure_time=" + str(ride_data["Request Time"])

    request_url = f"https://maps.googleapis.com/maps/api/directions/"
    request_url += f"{output_format}?{endpoints}&key={api_key}&{mode}&{departure_time}"

    return request_url


def retrieve_rides(filename: str) -> list:
    """Retrieve all start & end coordinates from EPP data file."""
    rides_df = pd.read_csv(filename)
    all_routes = []
    for i in range(rides_df.shape[0]):
        start_lat = rides_df.iloc[i]["Pickup Latitude"]
        start_long = rides_df.iloc[i]["Pickup Longitude"]
        end_lat = rides_df.iloc[i]["Drop Off Latitude"]
        end_long = rides_df.iloc[i]["Drop Off Longitude"]
        id_ = rides_df.iloc[i]["ID"]

        request_date = rides_df.iloc[i]["Request Date"]
        request_time = rides_df.iloc[i]["Request Time"]

        source_epoch_time = calculate_epoch_time(request_date, request_time)
        target_week_epoch = calculate_epoch_time(TARGET_WEEK, "5:00 PM") # time_str here is not used. Only provided to fulfill argument requirements.
        epoch_time = massage_time(source_epoch_time, target_week_epoch)
        

        route_data = {"Start": (start_lat, start_long), "End": (end_lat,end_long), "ID": id_, "Request Time": epoch_time}
        all_routes.append(route_data)

    return all_routes


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
    for ride in all_rides:
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
                if check_transit_mode(request_json): #ensures no driving directions were given
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
                text = "".join(line for line in file)

            #these skip archived results that do not provide public transit direction
            if api_call_results["status"] == "ZERO_RESULTS": #this occurs when Google could not find a reasonable connecting route
                continue

            travel_modes = get_travel_modes(api_call_results)
            if "DRIVING" in travel_modes:  # ensures no driving directions were given
                print("Driving route detected: " + str(ride["ID"]))
                continue

            duration = api_call_results["routes"][0]["legs"][0]["duration"]["text"]
            ride["Transit Duration"] = duration
            ride["Travel Mode"] = travel_modes

    return rides


def get_travel_modes(request_json):
    """Determines all travel modes used for a specific route."""
    directions = request_json["routes"][0]["legs"][0]["steps"]
    travel_modes = {step["travel_mode"] for step in directions}

    return travel_modes


def calculate_epoch_time(date_str, time_str)->int:
    """Determines seconds since start of epoch based on local time entry."""
    # convert date info into struct_time object
    split_date = date_str.split('/')
    for i in range(len(split_date)):
        if len(split_date[i]) == 1:
            split_date[i] = '0' + split_date[i] #formatting requires double-digit entries for days & months
    fixed_date = '/'.join(split_date)
    date_format = "%m/%d/%Y"
    date_struct = time.strptime(fixed_date, date_format)  # documentation https://docs.python.org/3.12/library/datetime.html#strftime-and-strptime-behavior

    # convert time info into struct_time object
    if len(time_str) == 7:
        time_str = '0' + time_str #double-digit formatting is also required for minutes and hours
    time_format = "%I:%M %p"
    time_struct = time.strptime(time_str, time_format)

    #combined into a single struct_time object
    input_tuple = (date_struct.tm_year, #year
                   date_struct.tm_mon, #month
                   date_struct.tm_mday, #day
                   time_struct.tm_hour + (LOCAL_TZ - DATA_TZ), #hour
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


def retrieve_api_key(file_name: str) -> str:
    """Retrieves the contents of the specified file."""
    api_key = ""
    with open(file_name, "r") as file:
        api_key = file.read()

    assert api_key != ""

    return api_key


def archive_api_call_results(result_json: dict, route_id: int):
    """Archives results of api calls for future reference."""
    path = getcwd() + "\\archive"
    if not isdir(path): # check for existence of archive folder, if it does not exist create it
        mkdir(path)

    serialized_json = json.dumps(result_json, indent=4)
    with open(f"{path}\\{route_id}.json", "w+") as file:
        file.write(serialized_json)


def create_error_record():
    pass


def test(ride_data):
    api_key = retrieve_api_key(API_KEY_FILE_NAME)
    request_url = construct_request(ride_data, api_key)
    print(request_url)
    route = requests.get(request_url)
    request_json = route.json()
    duration = request_json["routes"][0]["legs"][0]["duration"]["text"]
    print(duration)

    archive_api_call_results(request_json, "test")


def load_json_by_id(ride_id: int) -> dict:
    path = getcwd() + f"\\archive\\{ride_id}.json"
    with open(path, 'r') as file:
        api_call_results = json.load(file)
    return api_call_results


def construct_api_call_for_id(ride_id: int) -> str:
    """Creates the html address used to make the call for a specific ride."""
    api_key = retrieve_api_key(API_KEY_FILE_NAME)
    all_rides = retrieve_rides(RIDES_FILE_NAME)
    api_call_html = construct_request(all_rides[ride_id], api_key)
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


if __name__ == "__main__":
    api_key = retrieve_api_key(API_KEY_FILE_NAME)
    all_rides= retrieve_rides(RIDES_FILE_NAME)

    if NEW_DATA:
        execute_all_api_calls(all_rides, api_key)

    all_rides = add_transit_durations(all_rides)

    transit_duration_df = pool_data(all_rides)
    # transit_start_df = transit_duration_df[["ID", "Pickup Latitude", "Pickup Longitude", "Transit Duration"]]
    # transit_end_df = transit_duration_df[["ID", "Drop Off Latitude", "Drop Off Longitude", "Transit Duration"]]
    # transit_start_df.to_csv("Transit_Duration_Start_Coords Decouple Test.csv")
    # transit_end_df.to_csv("Transit_Duration_End_Coords Decouple Test.csv")
